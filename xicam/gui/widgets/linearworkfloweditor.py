import pickle
from qtpy.QtCore import *
from qtpy.QtGui import *
from qtpy.QtWidgets import *
from xicam.core.execution.workflow import Workflow
from pyqtgraph.parametertree import ParameterTree, Parameter
from xicam.gui.static import path
from xicam.plugins import manager as pluginmanager
from functools import partial


# WorkflowEditor
#  WorkflowProcessEditor
# WorkflowWidget
#  LinearWorkflowView
#   WorkflowModel


class WorkflowEditor(QSplitter):
    sigWorkflowChanged = Signal(object)

    def __init__(self, workflow: Workflow):
        super(WorkflowEditor, self).__init__()
        self.setOrientation(Qt.Vertical)

        self.processeditor = WorkflowProcessEditor()
        self.workflowview = LinearWorkflowView(WorkflowModel(workflow))

        self.addWidget(self.processeditor)
        self.addWidget(WorkflowWidget(self.workflowview))

        self.workflowview.sigShowParameter.connect(lambda parameter: self.setParameters(parameter))

        workflow.attach(partial(self.sigWorkflowChanged.emit, workflow))

    def setParameters(self, parameter: Parameter):

        parameter.blockSignals(True)
        for child in parameter.children():
            child.blockSignals(True)
        self.processeditor.setParameters(parameter, showTop=False)
        QApplication.processEvents()
        parameter.blockSignals(False)
        for child in parameter.children():
            child.blockSignals(False)


class WorkflowProcessEditor(ParameterTree):
    pass


class WorkflowWidget(QWidget):
    sigAddFunction = Signal(object)

    def __init__(self, workflowview: QAbstractItemView):
        super(WorkflowWidget, self).__init__()

        self.view = workflowview

        self.toolbar = QToolBar()
        addfunctionmenu = QToolButton()
        functionmenu = QMenu()
        for plugin in pluginmanager.getPluginsOfCategory("ProcessingPlugin"):
            functionmenu.addAction(plugin.name, partial(self.addProcess, plugin.plugin_object, autoconnectall=True))
        addfunctionmenu.setMenu(functionmenu)
        addfunctionmenu.setIcon(QIcon(path("icons/addfunction.png")))
        addfunctionmenu.setText("Add Function")
        addfunctionmenu.setPopupMode(QToolButton.InstantPopup)
        self.toolbar.addWidget(addfunctionmenu)
        # self.toolbar.addAction(QIcon(path('icons/up.png')), 'Move Up')
        # self.toolbar.addAction(QIcon(path('icons/down.png')), 'Move Down')
        self.toolbar.addAction(QIcon(path("icons/folder.png")), "Load Workflow")
        self.toolbar.addAction(QIcon(path("icons/trash.png")), "Delete Operation", self.deleteProcess)

        v = QVBoxLayout()
        v.addWidget(self.view)
        v.addWidget(self.toolbar)
        v.setContentsMargins(0, 0, 0, 0)
        self.setLayout(v)

    def addProcess(self, process, autoconnectall=True):
        self.view.model().workflow.addProcess(process(), autoconnectall)
        print("selected new row:", self.view.model().rowCount() - 1)
        self.view.setCurrentIndex(self.view.model().index(self.view.model().rowCount() - 1, 0))

    def deleteProcess(self):
        for index in self.view.selectedIndexes():
            process = self.view.model().workflow._processes[index.row()]
            self.view.model().workflow.removeProcess(process)


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
            process = self.model().workflow._processes[self.selectedIndexes()[0].row()]
            self.sigShowParameter.emit(process.parameter)
        else:
            self.sigShowParameter.emit(Parameter(name="empty"))
        for child in self.children():
            if hasattr(child, "repaint"):
                child.repaint()

        selectedrows = set(map(lambda index: index.row(), self.selectedIndexes()))
        for row in range(self.model().rowCount()):
            widget = self.indexWidget(self.model().index(row, 1))
            if hasattr(widget, "setSelectedVisibility"):
                widget.setSelectedVisibility(row in selectedrows)
        self.resizeRowsToContents()


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
        process = self.workflow._processes[srcindex]
        self.workflow.removeProcess(process)
        self.workflow.insertProcess(parent.row(), process)
        self.workflow.autoConnectAll()
        return True

    def supportedDropActions(self):
        return Qt.CopyAction | Qt.MoveAction

    def flags(self, index):
        if not index.isValid():
            return Qt.ItemIsEnabled
        return Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsDragEnabled | Qt.ItemIsDropEnabled

    def rowCount(self, *args, **kwargs):
        return len(self.workflow._processes)

    def columnCount(self, *args, **kwargs):
        return 2

    def data(self, index, role):
        process = self.workflow._processes[index.row()]
        if not index.isValid():
            return None
        elif role != Qt.DisplayRole:
            return None
        elif index.column() == 0:
            return partial(self.workflow.toggleDisableProcess, process, autoconnectall=True)
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
            process = self.view.model().workflow._processes[index.row()]
            widget = HintsWidget(process, self.view, index)
            self.view.setIndexWidget(index, widget)


class HintsWidget(QWidget):
    def __init__(self, process, view, index):
        super(HintsWidget, self).__init__()
        self.view = view
        self.setLayout(QGridLayout())
        self.layout().addWidget(QLabel(process.name), 0, 0, 1, 2)
        self.hints = process.hints

        enabledhints = [hint for hint in self.hints if hint.enabled]

        for i, hint in enumerate(enabledhints):
            enablebutton = QPushButton(icon=enableicon)
            sp = QSizePolicy()
            sp.setWidthForHeight(True)
            enablebutton.setSizePolicy(sp)
            enablebutton.setVisible(False)
            label = QLabel(hint.name)
            label.setVisible(False)
            self.layout().addWidget(enablebutton, i + 1, 0, 1, 1)
            self.layout().addWidget(label)

    def setSelectedVisibility(self, selected):
        for row in range(1, self.layout().rowCount()):
            self.layout().itemAtPosition(row, 0).widget().setVisible(selected)
            self.layout().itemAtPosition(row, 1).widget().setVisible(selected)


class DeleteDelegate(QItemDelegate):
    def __init__(self, parent):
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
    def __init__(self, parent):
        super(DisableDelegate, self).__init__(parent)
        self._parent = parent

    def paint(self, painter, option, index):
        if not self._parent.indexWidget(index):
            button = QToolButton(self.parent())
            button.setText("i")
            button.setAutoRaise(True)

            button.setIcon(enableicon)
            button.setCheckable(True)
            sp = QSizePolicy()
            sp.setWidthForHeight(True)
            button.setSizePolicy(sp)
            button.clicked.connect(index.data())

            self._parent.setIndexWidget(index, button)


enableicon = QIcon()
enableicon.addPixmap(QPixmap(path("icons/enable.png")), state=enableicon.Off)
enableicon.addPixmap(QPixmap(path("icons/disable.png")), state=enableicon.On)
