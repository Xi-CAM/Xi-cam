from collections import defaultdict
from qtpy.QtCore import QAbstractListModel, QMimeData, Qt, Signal, QVariant, QModelIndex
from qtpy.QtGui import QIcon
from qtpy.QtWidgets import QSplitter, QWidget, QAbstractItemView, QToolBar, QToolButton, QMenu, \
    QVBoxLayout, QListView, QPushButton, QCheckBox, \
    QHBoxLayout
from xicam.core.execution.workflow import Workflow
from pyqtgraph.parametertree import ParameterTree
from pyqtgraph.parametertree.parameterTypes import GroupParameter
from xicam.gui.static import path
from typing import Iterable, Any, Callable
from xicam.plugins import manager as pluginmanager, OperationPlugin
from xicam.core import threads
from functools import partial


# WorkflowEditor
#  WorkflowOperationEditor
# WorkflowWidget
#  LinearWorkflowView
#   WorkflowModel

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

    def __init__(self, workflow: Workflow, operation_filter: Callable[[OperationPlugin], bool] = None, **kwargs):
        super(WorkflowEditor, self).__init__()
        self.workflow = workflow
        self.kwargs = kwargs
        self.setOrientation(Qt.Vertical)

        self.operationeditor = WorkflowOperationEditor()
        self.workflowview = LinearWorkflowView(WorkflowModel(workflow))

        self.addWidget(self.operationeditor)
        workflow_widget = WorkflowWidget(self.workflowview, operation_filter=operation_filter)
        self.addWidget(workflow_widget)
        workflow_widget.sigRunWorkflow.connect(self.sigRunWorkflow.emit)
        workflow_widget.sigRunWorkflow.connect(self.run_workflow)
        # Should this work internally? How would the start operations get their inputs?
        # Would the ExamplePlugin need to explicitly set the parameter value (even for hidden image)?
        # It would be nice to just have this work easily... (to ExamplePlugin's perspective)
        # workflow_widget.sigRunWorkflow.connect(self.run_workflow)
        # TODO make work for autorun...
        # OR is this the outside class's respsonsibility (see SAXSGUIPlugin.maskeditor)

        self.workflowview.sigShowParameter.connect(self.setParameters)

        workflow.attach(self.sigWorkflowChanged.emit)

    def run_workflow(self, **kwargs):
        mixed_kwargs = self.kwargs.copy()
        mixed_kwargs.update(kwargs)
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

    def __init__(self, workflowview: QAbstractItemView, operation_filter: Callable[[OperationPlugin], bool] = None):
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
        # Defer menu population to once the plugins have been loaded; otherwise, the menu may not contain anything
        # if this widget is init'd before all plugins have been loaded.
        self.functionmenu = QMenu()
        self.functionmenu.aboutToShow.connect(self.populateFunctionMenu)
        self.addfunctionmenu.setMenu(self.functionmenu)
        self.addfunctionmenu.setPopupMode(QToolButton.InstantPopup)
        self.toolbar.addWidget(self.addfunctionmenu)
        # self.toolbar.addAction(QIcon(path('icons/up.png')), 'Move Up')
        # self.toolbar.addAction(QIcon(path('icons/down.png')), 'Move Down')
        self.toolbar.addAction(QIcon(path("icons/folder.png")), "Load Workflow")
        self.toolbar.addAction(QIcon(path("icons/trash.png")), "Delete Operation", self.deleteOperation)

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
        workflowmodel.workflow.attach(self.showCurrentParameter)
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
        self.workflow = workflow
        super(WorkflowModel, self).__init__()

        self.workflow.attach(self.layoutChanged.emit)

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
            return QVariant()
        elif role == Qt.CheckStateRole:
            disabled = self.workflow.disabled(operation)
            if disabled:
                return Qt.Unchecked
            else:
                return Qt.Checked
        elif role == Qt.DisplayRole:
            return operation.name
        else:
            return QVariant()

    def setData(self, index: QModelIndex, value: Any, role: int = ...) -> bool:
        if role == Qt.CheckStateRole:
            self.workflow.set_disabled(self.workflow.operations[index.row()], not value)
            return True
