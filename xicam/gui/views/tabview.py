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

# TODO:
#   mapping : {intent obj: widget}
#   use mapping to determine if a widget already exists in the tab view (if so, don't add a new one)
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
            canvas.sigInteractiveAction.connect(self.sigInteractiveAction, type=Qt.UniqueConnection)
        else:
            canvas = self._intents_to_widget[intent]
        return canvas

    def rowsInserted(self, parent: QModelIndex, start: int, end: int) -> None:
        for i in range(start, end+1):
            index = self.model().index(i, 0, parent)
            tab_title = self.model().data(index, Qt.DisplayRole)
            canvas = self.getWidgetFromIndex(index)
            # only insert tab if widget not in mapping
            if canvas not in self._intents_to_widget.values():
                self.widget.insertTab(i, canvas, tab_title)
                self._intents_to_widget[index.internalPointer()] = canvas

    def rowsAboutToBeRemoved(self, parent: QModelIndex, start: int, end: int) -> None:
        # TODO
        # unrender
        # if true: canvas can be removed (remove tab)
        # then remove entry from mapping
        # TODO:
        #    this doesn't work! the rows passed don't exist in the IntentsModel
        #    (the intents have been unchecked, only checked intents appear as valid rows)
        # for i in reversed(range(start, end+1)):
        #     index = self.model().index(i, 0, parent)  # TODO cant use index here (See above)
        #     canvas = self.getWidgetFromIndex(index)
        #     can_remove = canvas.unrender(canvas)
        #     if can_remove:
        #         self.widget.removeTab(i)
        #         del self._intents_to_widget[index.internalPointer()]
        for intent in self.model().intents_to_remove:
            canvas = self._intents_to_widget[intent]
            can_remove = canvas.unrender(intent)
            if can_remove:
                self.widget.removeTab(self.widget.indexOf(canvas))
                del self._intents_to_widget[intent]
