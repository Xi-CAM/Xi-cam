import pickle
from qtpy.QtCore import QAbstractTableModel, QMimeData, Qt, Signal, QSize
from qtpy.QtGui import QIcon, QPixmap
from qtpy.QtWidgets import (
    QSplitter,
    QApplication,
    QWidget,
    QAbstractItemView,
    QToolBar,
    QToolButton,
    QMenu,
    QVBoxLayout,
    QTableView,
    QItemDelegate,
    QGridLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QHeaderView,
)
from xicam.core.execution.workflow import Workflow
from xicam.plugins import OperationPlugin
from pyqtgraph.parametertree import ParameterTree, Parameter
from pyqtgraph.parametertree.parameterTypes import GroupParameter
from xicam.gui.static import path
from xicam.plugins import manager as pluginmanager
from functools import partial
from typing import List
from xicam.plugins import manager as pluginmanager, OperationPlugin
from functools import partial, lru_cache


# WorkflowEditor
#  WorkflowOperationEditor
# WorkflowWidget
#  LinearWorkflowView
#   WorkflowModel


class WorkflowEditor(QSplitter):
    sigWorkflowChanged = Signal()

    def __init__(self, workflow: Workflow):
        super(WorkflowEditor, self).__init__()
        self.workflow = workflow
        self.setOrientation(Qt.Vertical)

        self.operationeditor = WorkflowOperationEditor()
        self.workflowview = LinearWorkflowView(WorkflowModel(workflow))

        self.addWidget(self.operationeditor)
        self.addWidget(WorkflowWidget(self.workflowview))

        self.workflowview.sigShowParameter.connect(self.setParameters)

        workflow.attach(self.sigWorkflowChanged.emit)

    def setFixed(self, operation: OperationPlugin, param_name: str, value):
        operation.fixed[param_name] = value

    def setValue(self, operation: OperationPlugin, param_name: str, value):
        operation.filled_values[param_name] = value

    def setParameters(self, operation: OperationPlugin):
        parameter = operation.as_parameter()
        group = GroupParameter(name="Selected Operation", children=parameter)
        operation.wireup_parameter(group)
        for child, parameter in zip(group.children(), parameter):
            # wireup signals to update the workflow
            if parameter.get("fixable"):
                child.sigFixToggled.connect(partial(self.setFixed, operation, child.name))
            child.sigValueChanged.connect(partial(self.setValue, operation, child.name))

        group.blockSignals(True)
        for child in group.children():
            child.blockSignals(True)
        self.operationeditor.setParameters(group, showTop=False)
        QApplication.processEvents()
        group.blockSignals(False)
        for child in group.children():
            child.blockSignals(False)


class WorkflowOperationEditor(ParameterTree):
    pass


class WorkflowWidget(QWidget):
    sigAddFunction = Signal(object)

    def __init__(self, workflowview: QAbstractItemView):
        super(WorkflowWidget, self).__init__()

        self.view = workflowview

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
        v.addWidget(self.toolbar)
        v.setContentsMargins(0, 0, 0, 0)
        self.setLayout(v)

    def populateFunctionMenu(self):
        self.functionmenu.clear()
        sortingDict = {}
        for plugin in pluginmanager.get_plugins_of_type("OperationPlugin"):
            typeOfOperationPlugin = plugin.getCategory()
            if not typeOfOperationPlugin in sortingDict.keys():
                sortingDict[typeOfOperationPlugin] = []
            sortingDict[typeOfOperationPlugin].append(plugin)
        for key in sortingDict.keys():
            self.functionmenu.addSeparator()
            self.functionmenu.addAction(key)
            self.functionmenu.addSeparator()
            for plugin in sortingDict[key]:
                self.functionmenu.addAction(plugin.name, partial(self.addOperation, plugin, autoconnectall=True))

    def addOperation(self, operation: OperationPlugin, autoconnectall=True):
        self.view.model().workflow.addOperation(operation(), autoconnectall)
        print("selected new row:", self.view.model().rowCount() - 1)
        self.view.setCurrentIndex(self.view.model().index(self.view.model().rowCount() - 1, 0))

    def deleteOperation(self):
        for index in self.view.selectedIndexes():
            operation = self.view.model().workflow.operations[index.row()]
            self.view.model().workflow.remove_operation(operation)


class LinearWorkflowView(QTableView):
    sigShowParameter = Signal(object)

    def __init__(self, workflowmodel=None, *args, **kwargs):
        super(LinearWorkflowView, self).__init__(*args, **kwargs)

        self.setItemDelegateForColumn(0, DisableDelegate(self))
        self.setItemDelegateForColumn(1, HintsDelegate(self))

        self.setModel(workflowmodel)
        workflowmodel.workflow.attach(self.selectionChanged)

        self.horizontalHeader().close()
        # self.horizontalHeader().setStretchLastSection(True)
        self.horizontalHeader().setResizeMode(QHeaderView.ResizeToContents)
        self.horizontalHeader().setResizeMode(1, QHeaderView.Stretch)

        # self.horizontalHeader().setSectionMovable(True)
        # self.horizontalHeader().setDragEnabled(True)
        # self.horizontalHeader().setDragDropMode(QAbstractItemView.InternalMove)
        self.verticalHeader().setResizeMode(QHeaderView.ResizeToContents)
        self.setDragDropMode(QAbstractItemView.InternalMove)
        self.setDragEnabled(True)
        self.setDropIndicatorShown(True)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)

    def selectionChanged(self, selected=None, deselected=None):
        if self.selectedIndexes() and self.selectedIndexes()[0].row() < self.model().rowCount():
            operation = self.model().workflow.operations[self.selectedIndexes()[0].row()]  # type: OperationPlugin
            self.sigShowParameter.emit(operation)
        else:
            self.sigShowParameter.emit(None)
        for child in self.children():
            if hasattr(child, "repaint"):
                child.repaint()

        selectedrows = set(map(lambda index: index.row(), self.selectedIndexes()))
        for row in range(self.model().rowCount()):
            widget = self.indexWidget(self.model().index(row, 1))
            if hasattr(widget, "setSelectedVisibility"):
                widget.setSelectedVisibility(row in selectedrows)
        # self.resizeRowsToContents()


class WorkflowModel(QAbstractTableModel):
    def __init__(self, workflow: Workflow):
        self.workflow = workflow
        super(WorkflowModel, self).__init__()

        self.workflow.attach(partial(self.layoutChanged.emit))

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
        return Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsDragEnabled | Qt.ItemIsDropEnabled

    def rowCount(self, *args, **kwargs):
        return len(self.workflow.operations)

    def columnCount(self, *args, **kwargs):
        return 2

    def data(self, index, role):
        operation = self.workflow.operations[index.row()]
        if not index.isValid():
            return None
        elif role != Qt.DisplayRole:
            return None
        elif index.column() == 0:
            return partial(self.workflow.toggle_disabled, operation)
        elif index.column() == 1:
            # return getattr(process, 'name', process.__class__.__name__)
            return None
        return ""

    def headerData(self, col, orientation, role):
        return None


class HintsDelegate(QItemDelegate):
    def __init__(self, parent):
        super(HintsDelegate, self).__init__(parent=parent)
        self.view = parent

    def paint(self, painter, option, index):
        if not (self.view.indexWidget(index)):
            # selected = index in map(lambda index: index.row, self.view.selectedIndexes())
            operation = self.view.model().workflow.operations[index.row()]
            widget = HintsWidget(operation, self.view, index)
            self.view.setIndexWidget(index, widget)


class HintsWidget(QWidget):
    def __init__(self, operation, view, index):
        super(HintsWidget, self).__init__()
        self.view = view
        self.setLayout(QGridLayout())
        self.layout().addWidget(QLabel(operation.name), 0, 0, 1, 2)
        self.hints = operation.hints

        enabledhints = [hint for hint in self.hints if hint.enabled]

        for i, hint in enumerate(enabledhints):
            enablebutton = QPushButton(icon=mk_enableicon())
            sp = QSizePolicy()
            sp.setWidthForHeight(True)
            enablebutton.setSizePolicy(sp)
            enablebutton.setVisible(False)
            label = QLabel(hint.name)
            label.setVisible(False)
            self.layout().addWidget(enablebutton, i + 1, 0, 1, 1)
            self.layout().addWidget(label)

        self.name = operation.name

        print("size1:", operation.name, self.sizeHint())

    def setSelectedVisibility(self, selected):
        for row in range(1, self.layout().rowCount()):
            self.layout().itemAtPosition(row, 0).widget().setVisible(selected)
            self.layout().itemAtPosition(row, 1).widget().setVisible(selected)
        print("size2:", self.name, self.sizeHint())

    def sizeHint(self):
        return QSize(30, 30)


class DeleteDelegate(QItemDelegate):
    def __init__(self, parent=None):
        super(DeleteDelegate, self).__init__(parent)
        self._parent = parent

    def paint(self, painter, option, index):
        if not self._parent.indexWidget(index):
            button = QToolButton(self.parent())
            button.setAutoRaise(True)
            button.setText("Delete Operation")
            button.setIcon(QIcon(path("icons/trash.png")))
            sp = QSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)
            sp.setWidthForHeight(True)
            button.setSizePolicy(sp)
            button.clicked.connect(index.data())

            self._parent.setIndexWidget(index, button)


class DisableDelegate(QItemDelegate):
    class DelegateClass(QToolButton):
        def __init__(self, parent=None):
            super(DisableDelegate.DelegateClass, self).__init__(parent=parent)
            self.setText("i")
            self.setAutoRaise(True)

            self.setIcon(mk_enableicon())
            self.setCheckable(True)
            sp = QSizePolicy()
            sp.setWidthForHeight(True)
            self.setSizePolicy(sp)

    def __init__(self, parent):
        super(DisableDelegate, self).__init__(parent)
        self._parent = parent

    def paint(self, painter, option, index):
        if not self._parent.indexWidget(index):
            button = self.DelegateClass(self.parent())
            button.clicked.connect(index.data())
            self._parent.setIndexWidget(index, button)

    def sizeHint(self, QStyleOptionViewItem, QModelIndex):
        return QSize(30, 30)


@lru_cache(1)
def mk_enableicon():
    enableicon = QIcon()
    enableicon.addPixmap(QPixmap(path("icons/enable.png")), state=enableicon.Off)
    enableicon.addPixmap(QPixmap(path("icons/disable.png")), state=enableicon.On)
    return enableicon
