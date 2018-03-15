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

        self.workflowview.sigShowParameter.connect(
            lambda parameter: self.processeditor.setParameters(parameter, showTop=False))

        workflow.attach(partial(self.sigWorkflowChanged.emit, workflow))


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
        for plugin in pluginmanager.getPluginsOfCategory('ProcessingPlugin'):
            functionmenu.addAction(plugin.name, partial(self.addProcess, plugin.plugin_object,
                                                        autoconnectall=True))
        addfunctionmenu.setMenu(functionmenu)
        addfunctionmenu.setIcon(QIcon(path('icons/addfunction.png')))
        addfunctionmenu.setText('Add Function')
        addfunctionmenu.setPopupMode(QToolButton.InstantPopup)
        self.toolbar.addWidget(addfunctionmenu)
        # self.toolbar.addAction(QIcon(path('icons/up.png')), 'Move Up')
        # self.toolbar.addAction(QIcon(path('icons/down.png')), 'Move Down')
        self.toolbar.addAction(QIcon(path('icons/folder.png')), 'Load Workflow')
        self.toolbar.addAction(QIcon(path('icons/trash.png')), 'Clear Workflow')

        v = QVBoxLayout()
        v.addWidget(self.view)
        v.addWidget(self.toolbar)
        v.setContentsMargins(0, 0, 0, 0)
        self.setLayout(v)

    def addProcess(self, process, autoconnectall=True):
        self.view.model().workflow.addProcess(process(), autoconnectall)
        print('selected new row:', self.view.model().rowCount() - 1)
        self.view.setCurrentIndex(self.view.model().index(self.view.model().rowCount() - 1, 0))

class LinearWorkflowView(QTableView):
    sigShowParameter = Signal(object)

    def __init__(self, workflowmodel=None, *args, **kwargs):
        super(LinearWorkflowView, self).__init__(*args, **kwargs)
        self.setItemDelegateForColumn(0, DisableDelegate(self))
        self.setItemDelegateForColumn(2, DeleteDelegate(self))

        self.setModel(workflowmodel)
        workflowmodel.workflow.attach(self.selectionChanged)

        self.horizontalHeader().close()
        # self.horizontalHeader().setStretchLastSection(True)
        self.horizontalHeader().setResizeMode(QHeaderView.ResizeToContents)
        self.horizontalHeader().setResizeMode(1, QHeaderView.Stretch)

        # self.horizontalHeader().setSectionMovable(True)
        # self.horizontalHeader().setDragEnabled(True)
        # self.horizontalHeader().setDragDropMode(QAbstractItemView.InternalMove)
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
            self.sigShowParameter.emit(Parameter(name='empty'))
        for child in self.children():
            if hasattr(child, 'repaint'): child.repaint()


class WorkflowModel(QAbstractTableModel):
    def __init__(self, workflow: Workflow):
        self.workflow = workflow
        super(WorkflowModel, self).__init__()


        self.workflow.attach(partial(self.layoutChanged.emit))

    def mimeTypes(self):
        return ['text/plain']

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
        return Qt.ItemIsEnabled | Qt.ItemIsSelectable | \
               Qt.ItemIsDragEnabled | Qt.ItemIsDropEnabled

    def rowCount(self, *args, **kwargs):
        return len(self.workflow._processes)

    def columnCount(self, *args, **kwargs):
        return 3

    def data(self, index, role):
        process = self.workflow._processes[index.row()]
        if not index.isValid():
            return None
        elif role != Qt.DisplayRole:
            return None
        elif index.column() == 0:
            return partial(self.workflow.toggleDisableProcess, process, autoconnectall=True)
        elif index.column() == 1:
            return getattr(process, 'name', process.__class__.__name__)
        elif index.column() == 2:
            return partial(self.workflow.removeProcess, index=index.row(), autoconnectall=True)
        return ''

    def headerData(self, col, orientation, role):
        return None


class DeleteDelegate(QItemDelegate):
    def __init__(self, parent):
        super(DeleteDelegate, self).__init__(parent)
        self._parent = parent

    def paint(self, painter, option, index):
        if not self._parent.indexWidget(index):
            button = QToolButton(self.parent(), )
            button.setAutoRaise(True)
            button.setText('Delete Operation')
            button.setIcon(QIcon(path('icons/trash.png')))
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
            button.setText('i')
            button.setAutoRaise(True)
            icon = QIcon()
            icon.addPixmap(QPixmap(path('icons/enable.png')), state=icon.Off)
            icon.addPixmap(QPixmap(path('icons/disable.png')), state=icon.On)
            button.setIcon(icon)
            button.setCheckable(True)
            sp = QSizePolicy()
            sp.setWidthForHeight(True)
            button.setSizePolicy(sp)
            button.clicked.connect(index.data())

            self._parent.setIndexWidget(index, button)
