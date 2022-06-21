from qtpy.QtCore import Signal, Qt, QModelIndex, QPoint, QRect, QItemSelection
from qtpy.QtGui import QRegion
from qtpy.QtWidgets import QAbstractItemView, QHBoxLayout, QLabel, QTabWidget
from xicam.gui.actions import Action
from xicam.gui.canvases import XicamIntentCanvas
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
        ...

    def rowsAboutToBeRemoved(self, parent: QModelIndex, start: int, end: int) -> None:
        ...

    def getWidgetFromIndex(self, index: QModelIndex):
        raise NotImplementedError


class IntentsTabView(TabView):

    sigInteractiveAction = Signal(Action, XicamIntentCanvas)

    def __init__(self, parent=None):
        super(IntentsTabView, self).__init__(parent)

        self._intents_to_widget = {}

    def getWidgetFromIndex(self, index: QModelIndex):
        intent = index.internalPointer()
        # Need to lookup whether an intent is already mapped (rendered) to a canvas (tab widget)
        if intent not in self._intents_to_widget:
            canvas = self.model().data(index, IntentsModel.canvas_role)
            try:
                canvas.sigInteractiveAction.connect(self.sigInteractiveAction, type=Qt.UniqueConnection)
            except Exception as e:
                pass
        else:
            canvas = self._intents_to_widget[intent]
        return canvas

    def rowsInserted(self, parent: QModelIndex, start: int, end: int) -> None:
        for i in range(start, end+1):
            index = self.model().index(i, 0, parent)
            tab_title = self.model().data(index, Qt.DisplayRole)
            canvas = self.getWidgetFromIndex(index)
            intent = index.internalPointer()
            # only insert tab if widget not in mapping
            if canvas not in self._intents_to_widget.values():
                self.widget.insertTab(i, canvas, tab_title)
                self._intents_to_widget[intent] = canvas
            if intent not in self._intents_to_widget:
                self._intents_to_widget[intent] = canvas

    def rowsAboutToBeRemoved(self, parent: QModelIndex, start: int, end: int) -> None:
        # Ask IntentsModel for what intents are going to be removed (which have just been unchecked)

        self._remove_intents(self.model().intents_to_remove)

    def _remove_intents(self, intents):
        for intent in intents:
            canvas = self._intents_to_widget[intent]
            can_remove = canvas.unrender(intent)
            # When safe, remove the tab
            if can_remove:
                self.widget.removeTab(self.widget.indexOf(canvas))
            # make sure to remove the intent from the mapping
            del self._intents_to_widget[intent]

    def refresh(self):
        current_index = self.widget.currentIndex()
        self._remove_intents([self.model().index(i, 0).internalPointer() for i in range(self.widget.count())])
        self.rowsInserted(QModelIndex(), 0, self.model().rowCount())
        self.widget.setCurrentIndex(current_index)
