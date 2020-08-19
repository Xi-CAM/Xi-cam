
from collections import defaultdict
from qtpy.QtCore import QAbstractListModel, QMimeData, Qt, Signal,  QVariant, QModelIndex
from qtpy.QtGui import QIcon
from qtpy.QtWidgets import QSplitter,  QWidget, QAbstractItemView, QToolBar, QToolButton, QMenu, \
    QVBoxLayout, QListView, QPushButton,  QCheckBox, \
    QHBoxLayout
from xicam.core.execution.workflow import Workflow
from pyqtgraph.parametertree import ParameterTree
from pyqtgraph.parametertree.parameterTypes import GroupParameter
from xicam.gui.static import path
from typing import Iterable, Any
from xicam.plugins import manager as pluginmanager, OperationPlugin
from xicam.core import threads
from functools import partial


# WorkflowEditor
#  WorkflowOperationEditor
# WorkflowWidget
#  LinearWorkflowView
#   WorkflowModel

# TODO: Move Run buttons to subclass of WorkflowWidget

class WorkflowEditor(QSplitter):
    sigWorkflowChanged = Signal()
    sigRunWorkflow = Signal()

    def __init__(self, workflow: Workflow, **kwargs):
        super(WorkflowEditor, self).__init__()
        self.workflow = workflow
        self.kwargs = kwargs
        self.setOrientation(Qt.Vertical)

        self.operationeditor = WorkflowOperationEditor()
        self.workflowview = LinearWorkflowView(WorkflowModel(workflow))

        self.addWidget(self.operationeditor)
        workflow_widget = WorkflowWidget(self.workflowview)
        self.addWidget(workflow_widget)
        workflow_widget.sigRunWorkflow.connect(self.sigRunWorkflow.emit)
        # Should this work internally? How would the start operations get their inputs?
        # Would the ExamplePlugin need to explicitly set the parameter value (even for hidden image)?
        # It would be nice to just have this work easily... (to ExamplePlugin's perspective)
        # workflow_widget.sigRunWorkflow.connect(self.run_workflow)
        # TODO make work for autorun...
        # OR is this the outside class's respsonsibility (see SAXSGUIPlugin.maskeditor)

        self.workflowview.sigShowParameter.connect(self.setParameters)

        workflow.attach(self.sigWorkflowChanged.emit)

    def run_workflow(self, _):
        self.workflow.execute(**self.kwargs)

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

    @staticmethod
    def _unblock_group(group):
            group.blockSignals(False)
            for child in group.children():
                child.blockSignals(False)


class WorkflowOperationEditor(ParameterTree):
    pass


class WorkflowWidget(QWidget):
    sigAddFunction = Signal(object)
    sigRunWorkflow = Signal(object)
    # TODO -- emit Workflow from sigRunWorkflow

    def __init__(self, workflowview: QAbstractItemView):
        super(WorkflowWidget, self).__init__()

        self.view = workflowview

        self.autorun_checkbox = QCheckBox("Run Automatically")
        self.autorun_checkbox.setCheckState(Qt.Unchecked)
        self.autorun_checkbox.stateChanged.connect(self._autorun_state_changed)
        self.run_button = QPushButton("Run Workflow")
        self.run_button.clicked.connect(self.sigRunWorkflow.emit)
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

    def _run_workflow(self, _):
        self._workflow

    # TODO: support more than one depth of categories
    def populateFunctionMenu(self):
        self.functionmenu.clear()
        sortingDict = defaultdict(list)
        for plugin in pluginmanager.get_plugins_of_type("OperationPlugin"):
            typesOfOperationPlugin = plugin.categories
            if not typesOfOperationPlugin:
                typesOfOperationPlugin = ["Uncategorized"]  # put found operations into a default category
            for typeOfOperationPlugin in typesOfOperationPlugin:
                # TODO : should OperationPlugin be responsible for initializing categories
                # to some placeholder value (instead of [])?
                sortingDict[typeOfOperationPlugin].append(plugin)
        for key in sortingDict.keys():
            self.functionmenu.addSeparator()
            self.functionmenu.addAction(key[0])
            self.functionmenu.addSeparator()
            for plugin in sortingDict[key]:
                self.functionmenu.addAction(plugin.name, partial(self.addOperation, plugin, autoconnectall=True))

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
