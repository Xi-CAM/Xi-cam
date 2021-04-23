from collections import defaultdict, UserDict
from qtpy.QtCore import QAbstractListModel, QMimeData, Qt, Signal, QModelIndex
from qtpy.QtGui import QIcon
from qtpy.QtWidgets import QSplitter, QWidget, QAbstractItemView, QToolBar, QToolButton, QMenu, \
    QVBoxLayout, QListView, QPushButton, QCheckBox, \
    QHBoxLayout, QComboBox
from xicam.core.execution.workflow import Workflow
from pyqtgraph.parametertree import ParameterTree
from pyqtgraph.parametertree.parameterTypes import GroupParameter
from xicam.gui.static import path
from typing import Iterable, Any, Callable, Dict
from xicam.plugins import manager as pluginmanager, OperationPlugin
from xicam.core import threads
from xicam.core import msg
from functools import partial


# WorkflowEditor
#  WorkflowOperationEditor
# WorkflowWidget
#  LinearWorkflowView
#   WorkflowModel

class WorkflowDict(dict):
    def __setitem__(self, workflow, name):
        if name in set(self.values()):
            raise ValueError(f'A workflow with the same name already exists: {name}')
        super(WorkflowDict, self).__setitem__(workflow, name)


# TODO: Move Run buttons to subclass of WorkflowWidget

class MenuDict(defaultdict):
    def __init__(self):
        super(MenuDict, self).__init__(self._default)

    def _default(self, key):
        if key == "___":
            return []
        else:
            return MenuDict()

    def __missing__(self, key):
        if self.default_factory is None:
            raise KeyError(key)
        else:
            ret = self[key] = self.default_factory(key)
            return ret

    def __iter__(self):
        return iter(sorted(super(MenuDict, self).__iter__()))


class WorkflowEditor(QSplitter):
    sigWorkflowChanged = Signal()
    sigRunWorkflow = Signal()

    def __init__(self, workflow: Workflow,
                 operation_filter: Callable[[OperationPlugin], bool] = None,
                 kwargs_callable: Callable[[], dict] = None,
                 execute_iterative: bool = False,
                 workflows: Dict[Workflow, str] = None,
                 **kwargs):
        """
        A Workflow editor that shows each operation in insertion order. This is useful in simplistic workflows, typically
        when data passes from through a linear sequence. This order may not represent execution order when
        a workflow is programmatically composed, or when graph-based editing is supported in the future.

        Parameters
        ----------
        workflow : Workflow
            A workflow instance; may be initially empty.
        operation_filter: Callable[[OperationPlugin], bool]
            A callable that can be used to filter which operations to show in the "Add Operation" menu
        kwargs_callable: Callable[[], dict]
            A callable that gets called when run is triggered. This callable is expected to generate a dict of
            kwargs that will be passed into the workflow as inputs.
        execute_iterative: bool
            Determines if the attached workflow will be executed with `.execute` or `.execute_all`. When `.execute_all`
            is used, all input args get zipped, and the workflow is executed over each arg tuple.

        """
        super(WorkflowEditor, self).__init__()
        if workflows is None:
            workflows = WorkflowDict()
        if workflow not in workflows:
            workflows[workflow] = workflow.name
        self.kwargs = kwargs or dict()
        self.kwargs_callable = kwargs_callable
        self.execute_iterative = execute_iterative
        self.setOrientation(Qt.Vertical)

        self.operationeditor = WorkflowOperationEditor()
        self.workflowview = LinearWorkflowView(WorkflowModel(workflow))

        self.addWidget(self.operationeditor)
        self.workflow_widget = WorkflowWidget(self.workflowview, operation_filter=operation_filter, workflows=workflows)
        self.addWidget(self.workflow_widget)
        self.workflow_widget.sigRunWorkflow.connect(self.sigRunWorkflow.emit)
        self.workflow_widget.sigRunWorkflow.connect(self.run_workflow)
        # Should this work internally? How would the start operations get their inputs?
        # Would the ExamplePlugin need to explicitly set the parameter value (even for hidden image)?
        # It would be nice to just have this work easily... (to ExamplePlugin's perspective)
        # workflow_widget.sigRunWorkflow.connect(self.run_workflow)
        # TODO make work for autorun...
        # OR is this the outside class's respsonsibility (see SAXSGUIPlugin.maskeditor)

        self.workflowview.sigShowParameter.connect(self.setParameters)

        self.workflow.attach(self.sigWorkflowChanged.emit)

        # rebind widget attrs
        self.addWorkflow = self.workflow_widget.addWorkflow
        self.removeWorkflow = self.workflow_widget.removeWorkflow
        self.workflows = self.workflow_widget.workflows

        self.setToolTip("Workflow Editor")
        self.setWhatsThis("This widget is the Workflow Editor. "
                          "It is used to create linear workflows from installed operations. "
                          "Enable or disable an operation by clicking on its check or X. "
                          "Modify parameters of an operation by clicking on its text. ")

    @property
    def workflow(self):
        return self.workflowview.model().workflow

    @workflow.setter
    def workflow(self, new_workflow: Workflow):
        self.workflow.detach(self.sigWorkflowChanged.emit)
        self.workflowview.model().workflow = new_workflow
        self.workflow.attach(self.sigWorkflowChanged.emit)

    def run_workflow(self, **kwargs):
        mixed_kwargs = self.kwargs.copy()
        if self.kwargs_callable is not None:
            try:
                called_kwargs = self.kwargs_callable(self)
            except RuntimeError as e:
                # NOTE: we do not want to raise an exception here (we are in a connected Qt slot)
                # Grab the user-oriented message from the kwargs callable exception
                msg.notifyMessage(str(e), title="Run Workflow Error", level=msg.ERROR)
                msg.logError(e)
            else:
                mixed_kwargs.update(called_kwargs)
                mixed_kwargs.update(kwargs)

                if self.execute_iterative:
                    self.workflow.execute_all(**mixed_kwargs)
                else:
                    self.workflow.execute(**mixed_kwargs)

    def setParameters(self, operation: OperationPlugin):
        if operation:
            # Create a new Parameter from the emitted operation,
            # Then wire up its connections for use in a parameter tree.
            parameter = operation.as_parameter()
            group = GroupParameter(name='Selected Operation', children=parameter)
            operation.wireup_parameter(group)

            # Add the Parameter to the parameter tree
            group.blockSignals(True)
            for child in group.children():
                child.blockSignals(True)
            self.operationeditor.setParameters(group, showTop=False)
            threads.invoke_as_event(self._unblock_group, group)
        else:
            self.operationeditor.clear()

    @staticmethod
    def _unblock_group(group):
        group.blockSignals(False)
        for child in group.children():
            child.blockSignals(False)


class WorkflowOperationEditor(ParameterTree):
    pass


class WorkflowWidget(QWidget):
    sigAddFunction = Signal(object)
    sigRunWorkflow = Signal()

    # TODO -- emit Workflow from sigRunWorkflow

    def __init__(self, workflowview: QAbstractItemView,
                 operation_filter: Callable[[OperationPlugin], bool] = None,
                 workflows: Dict[Workflow, str] = None):
        super(WorkflowWidget, self).__init__()

        self.operation_filter = operation_filter
        self.view = workflowview

        self.autorun_checkbox = QCheckBox("Run Automatically")
        self.autorun_checkbox.setCheckState(Qt.Unchecked)
        self.autorun_checkbox.stateChanged.connect(self._autorun_state_changed)
        self.run_button = QPushButton("Run Workflow")
        self.run_button.clicked.connect(self.sigRunWorkflow.emit)
        self.view.model().workflow.attach(self._autorun)
        # TODO -- actually hook up the auto run OR dependent class needs to connect (see SAXSGUIPlugin)

        self.toolbar = QToolBar()
        self.addfunctionmenu = QToolButton()
        self.addfunctionmenu.setIcon(QIcon(path("icons/addfunction.png")))
        self.addfunctionmenu.setText("Add Function")
        self.addfunctionmenu.setToolTip("Add Operation")
        self.addfunctionmenu.setWhatsThis("This button can be used to add a new operation to the end of a workflow. "
                                          "A menu to select operations will be populated based on the installed "
                                          "operations' categories.")
        # Defer menu population to once the plugins have been loaded; otherwise, the menu may not contain anything
        # if this widget is init'd before all plugins have been loaded.
        self.functionmenu = QMenu()
        self.functionmenu.aboutToShow.connect(self.populateFunctionMenu)
        self.addfunctionmenu.setMenu(self.functionmenu)
        self.addfunctionmenu.setPopupMode(QToolButton.InstantPopup)

        self.workflows = WorkflowDict(workflows or {})

        self.workflow_menu = QMenu()
        self.workflow_menu.aboutToShow.connect(self.populateWorkflowMenu)
        self.workflow_selector = QToolButton()
        self.workflow_selector.setIcon(QIcon(path("icons/bookshelf.png")))
        self.workflow_selector.setText("Select Workflow")
        self.workflow_selector.setToolTip("Workflow Library")
        self.workflow_selector.setWhatsThis("This button allows switching between any stored workflows. "
                                            "(Stored workflows are typically defined programmatically "
                                            "in a GUI Plugin's modules.)")
        self.workflow_selector.setMenu(self.workflow_menu)
        self.workflow_selector.setPopupMode(QToolButton.InstantPopup)
        self.toolbar.addWidget(self.workflow_selector)

        self.toolbar.addWidget(self.addfunctionmenu)
        # self.toolbar.addAction(QIcon(path('icons/up.png')), 'Move Up')
        # self.toolbar.addAction(QIcon(path('icons/down.png')), 'Move Down')
        action = self.toolbar.addAction(QIcon(path("icons/save.png")), "Export Workflow")
        action.setEnabled(False)  # FIXME: implement export workflow feature
        action = self.toolbar.addAction(QIcon(path("icons/folder.png")), "Import Workflow")
        action.setEnabled(False)  # FIXME: implement import workflow feature

        action = self.toolbar.addAction(QIcon(path("icons/trash.png")), "Delete Operation", self.deleteOperation)
        action.setWhatsThis("This button removes the currently selected operation from the workflow. "\
                            "(The currently selected operation is highlighted. "\
                            "An operation is selected when its text is clicked in the workflow editor.")

        v = QVBoxLayout()
        v.addWidget(self.view)
        h = QHBoxLayout()
        h.addWidget(self.autorun_checkbox)
        h.addWidget(self.run_button)
        v.addLayout(h)
        v.addWidget(self.toolbar)
        v.setContentsMargins(0, 0, 0, 0)
        self.setLayout(v)

    def _autorun_state_changed(self, state):
        if state == Qt.Checked:
            self.run_button.setDisabled(True)
        else:
            self.run_button.setDisabled(False)

    def _autorun(self):
        if self.autorun_checkbox.isChecked():
            self.sigRunWorkflow.emit()

    def populateFunctionMenu(self):
        self.functionmenu.clear()
        sortingDict = MenuDict()
        operations = pluginmanager.get_plugins_of_type("OperationPlugin")
        if self.operation_filter is not None:
            operations = filter(self.operation_filter, operations)
        for operation in operations:

            categories = operation.categories
            if not categories:
                categories = [("Uncategorized",)]  # put found operations into a default category

            for categories_tuple in categories:
                if isinstance(categories_tuple, str):
                    categories_tuple = (categories_tuple,)
                submenu = sortingDict
                categories_list = list(categories_tuple)
                while categories_list:
                    category = categories_list.pop(0)
                    submenu = submenu[category]

                submenu['___'].append(operation)

        self._mkMenu(sortingDict)

    def populateWorkflowMenu(self):
        self.workflow_menu.clear()
        for workflow, workflow_name in self.workflows.items():
            self.workflow_menu.addAction(workflow_name, partial(self.setWorkflow, workflow))

    def _mkMenu(self, sorting_dict, menu=None):
        if menu is None:
            menu = self.functionmenu
            menu.clear()

        for key in sorting_dict:
            if key == '___':
                menu.addSeparator()
                for operation in sorting_dict['___']:
                    menu.addAction(operation.name, partial(self.addOperation, operation, autoconnectall=True))
            else:
                submenu = QMenu(title=key, parent=menu)
                menu.addMenu(submenu)
                self._mkMenu(sorting_dict[key], submenu)

    def setWorkflow(self, workflow: Workflow):
        self.view.model().workflow = workflow

    def addWorkflow(self, workflow: Workflow, name: str = None):
        if name is None:
            name = workflow.name
        if name in self.workflows:
            raise ValueError(f'A workflow already exists in this editor with the name "{name}"')
        self.workflows[name] = workflow

    def removeWorkflow(self, workflow):
        for name, match_workflow in self.workflows.items():
            if workflow == match_workflow:
                del self.workflows[name]

    def addOperation(self, operation: OperationPlugin, autoconnectall=True):
        self.view.model().workflow.add_operation(operation())
        if autoconnectall:
            self.view.model().workflow.auto_connect_all()
        print("selected new row:", self.view.model().rowCount() - 1)
        self.view.setCurrentIndex(self.view.model().index(self.view.model().rowCount() - 1, 0))

    def deleteOperation(self):
        index = self.view.currentIndex()
        operation = self.view.model().workflow.operations[index.row()]
        self.view.model().workflow.remove_operation(operation)
        self.view.setCurrentIndex(QModelIndex())


class DisablableListView(QListView):
    """
    Replaces the check indicator with checkmark/x images
    """

    def __init__(self, *args, **kwargs):
        super(DisablableListView, self).__init__(*args, **kwargs)
        # TODO: find an icon for indeterminate stae
        self.setStyleSheet("""
        QListView::indicator:checked {
            image: url(""" + path('icons/enable.png').replace('\\', '/') + """);
        }
        QListView::indicator:indeterminate {
            image: url(""" + path('icons/enable.png').replace('\\', '/') + """);
        }
        QListView::indicator:unchecked {
            image: url(""" + path('icons/disable.png').replace('\\', '/') + """);
        }""")


class LinearWorkflowView(DisablableListView):
    sigShowParameter = Signal(object)

    def __init__(self, workflowmodel=None, *args, **kwargs):
        super(LinearWorkflowView, self).__init__(*args, **kwargs)

        self.setModel(workflowmodel)
        # Lines commented below were causing long slow-downs when enable/disabling a tree
        # and when clicking a op (to show param tree)
        # Did we need all notifies to call showCurrentParameter? Probably not?
        # Did we need to call showCurrentParameter when the layoutChanges? Probably not?
        # workflowmodel._workflow.attach(self.showCurrentParameter)
        # workflowmodel.layoutChanged.connect(partial(self.showCurrentParameter, None))
        self.selectionModel().currentChanged.connect(self.showCurrentParameter)

        self.setDragDropMode(QAbstractItemView.InternalMove)
        self.setDragEnabled(True)
        self.setDropIndicatorShown(True)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)

        self.setWordWrap(False)

    def showCurrentParameter(self, *args):
        current = self.currentIndex()
        if current.isValid() and current.row() < self.model().rowCount():
            operation = self.model().workflow.operations[current.row()]  # type: OperationPlugin
            self.sigShowParameter.emit(operation)
        else:
            self.sigShowParameter.emit(None)


class WorkflowModel(QAbstractListModel):
    def __init__(self, workflow: Workflow):
        self._workflow = workflow
        super(WorkflowModel, self).__init__()

        self._workflow.attach(self.layoutChanged.emit)

    @property
    def workflow(self):
        return self._workflow

    @workflow.setter
    def workflow(self, new_workflow: Workflow):
        self._workflow.detach(self.layoutChanged.emit)
        self._workflow = new_workflow
        self._workflow.attach(self.layoutChanged.emit)
        self.layoutChanged.emit()

    def mimeTypes(self):
        return ["text/plain"]

    def mimeData(self, indexes):
        mimedata = QMimeData()
        mimedata.setText(str(indexes[0].row()))
        return mimedata

    def dropMimeData(self, data, action, row, column, parent):
        srcindex = int(data.text())
        operation = self.workflow.operations[srcindex]
        self.workflow.remove_operation(operation)
        self.workflow.insert_operation(parent.row(), operation)
        self.workflow.auto_connect_all()
        return True

    def supportedDropActions(self):
        return Qt.CopyAction | Qt.MoveAction

    def flags(self, index):
        if not index.isValid():
            return Qt.ItemIsEnabled
        return Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsDragEnabled | Qt.ItemIsDropEnabled | Qt.ItemIsUserCheckable

    def rowCount(self, *args, **kwargs):
        return len(self.workflow.operations)

    def data(self, index, role):
        operation = self.workflow.operations[index.row()]
        if not index.isValid():
            return None
        elif role == Qt.CheckStateRole:
            disabled = self.workflow.disabled(operation)
            if disabled:
                return Qt.Unchecked
            else:
                return Qt.Checked
        elif role == Qt.DisplayRole:
            return operation.name
        else:
            return None

    def setData(self, index: QModelIndex, value: Any, role: int = ...) -> bool:
        if role == Qt.CheckStateRole:
            self.workflow.set_disabled(self.workflow.operations[index.row()], not value)
            return True
