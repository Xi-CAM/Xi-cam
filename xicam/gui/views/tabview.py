from qtpy.QtCore import Qt, QModelIndex, QPoint, QRect, QItemSelection
from qtpy.QtGui import QRegion
from qtpy.QtWidgets import QAbstractItemView, QHBoxLayout, QLabel, QTabWidget
from xicam.gui.models.treemodel import IntentsModel


class TabView(QAbstractItemView):
    def __init__(self, parent=None):
        super(TabView, self).__init__(parent)
        self.widget = QTabWidget(parent)
        layout = QHBoxLayout()
        layout.addWidget(self.widget)
        self.setLayout(layout)
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().setSpacing(0)

    # Default implementations of qt pure virtuals
    def horizontalOffset(self) -> int:
        return 0

    def indexAt(self, p: QPoint) -> QModelIndex:
        return QModelIndex()

    def moveCursor(self, cursorAction: QAbstractItemView.CursorAction, modifiers) -> QModelIndex:
        return QModelIndex()

    def visualRect(self, index: QModelIndex) -> QRect:
        return QRect()

    def verticalOffset(self) -> int:
        return 0

    def visualRegionForSelection(self, selection: QItemSelection) -> QRegion:
        return QRegion()

    def currentChanged(self, current: QModelIndex, previous: QModelIndex) -> None:
        ...

    def dataChanged(self, topLeft, bottomRight, roles=None) -> None:
        ...

    def rowsInserted(self, parent: QModelIndex, start: int, end: int) -> None:
        for i in range(start, end+1):
            index = self.model().index(i, 0, parent)
            data = self.model().data(index, Qt.DisplayRole)
            canvas = self.getWidgetFromIndex(index)
            self.widget.insertTab(i, canvas, data)

    def rowsAboutToBeRemoved(self, parent: QModelIndex, start: int, end: int) -> None:
        for i in reversed(range(start, end+1)):
            self.widget.removeTab(i)

    def getWidgetFromIndex(self, index: QModelIndex):
        raise NotImplementedError


class IntentsTabView(TabView):
    def getWidgetFromIndex(self, index: QModelIndex):
        return self.model().data(index, IntentsModel.canvas_role)
