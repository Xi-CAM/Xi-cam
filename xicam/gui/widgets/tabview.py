from warnings import warn

from qtpy.QtWidgets import QTabBar, QMenu, QAction, QTabWidget
from qtpy.QtGui import QStandardItemModel, QMouseEvent
from qtpy.QtCore import QItemSelectionModel, QObject, Qt
from typing import List
from functools import partial
from xicam.core import msg


class TabView(QTabWidget):
    def __init__(
        self,
        catalogmodel: QStandardItemModel = None,
        selectionmodel: QItemSelectionModel = None,
        widgetcls=None,
        stream=None,
        field=None,
        bindings: List[tuple] = [],
        **kwargs,
    ):
        """

        Parameters
        ----------
        model
        widgetcls
        stream
        field
        bindings
            A list of tuples with pairs of bindings, s.t. the one item is the name of the attribute on widget cls holding a
            signal (to be mirrored across each new widget), and the second is the receiver.
        kwargs
        """
        super(TabView, self).__init__()
        self.setTabBar(ContextMenuTabBar())
        self.kwargs = kwargs

        self.setWidgetClass(widgetcls)
        self.catalogmodel = None
        self.selectionmodel = None
        if selectionmodel:
            self.setSelectionModel(selectionmodel)  # type: TabItemSelectionModel

        if catalogmodel:
            self.setCatalogModel(catalogmodel)

        self.stream = stream
        self.field = field
        self.bindings = bindings

        self.setTabsClosable(True)
        self.setDocumentMode(True)
        self.tabCloseRequested.connect(self.closeTab)

    def setCatalogModel(self, model: QStandardItemModel):
        self.catalogmodel = model
        if not self.selectionmodel:
            self.selectionmodel = TabItemSelectionModel(self)
        model.dataChanged.connect(self.dataChanged)

    def setHeaderModel(self, model):
        self.setCatalogModel(model)
        warn(DeprecationWarning())

    def setSelectionModel(self, model: QItemSelectionModel):
        self.selectionmodel = model
        self.selectionmodel.currentChanged.connect(lambda current, previous: self.setCurrentIndex(current.row()))
        self.currentChanged.connect(
            lambda i: self.selectionmodel.setCurrentIndex(self.catalogmodel.index(i, 0), QItemSelectionModel.Rows)
        )
        self.currentChanged.connect(
            lambda _: self.selectionmodel.setCurrentIndex(
                self.catalogmodel.index(self.currentIndex(), 0), QItemSelectionModel.ClearAndSelect
            )
        )

    def dataChanged(self, start, end):
        for i in range(self.catalogmodel.rowCount()):
            itemdata = None
            if hasattr(self.catalogmodel.item(i), "header"):
                itemdata = self.catalogmodel.item(i).header
            else:
                itemdata = self.catalogmodel.item(i).data(Qt.UserRole)

            if self.widget(i):
                if (hasattr(self.widget(i), "catalog") and self.widget(i).catalog == itemdata) or (
                    hasattr(self.widget(i), "header") and self.widget(i).header == itemdata
                ):
                    continue
            try:
                newwidget = self.widgetcls(itemdata, stream=self.stream, field=self.field, **self.kwargs)
            except Exception as ex:
                msg.logMessage(
                    f"A widget of type {self.widgetcls} could not be initialized with args: {itemdata, self.field, self.kwargs}"
                )
                msg.logError(ex)
                self.catalogmodel.removeRow(i)
                self.dataChanged(0, 0)
                return

            self.setCurrentIndex(self.insertTab(i, newwidget, self.catalogmodel.item(i).text()))

            for sender, receiver in self.bindings:
                if isinstance(sender, str):
                    sender = getattr(newwidget, sender)
                if isinstance(receiver, str):
                    receiver = getattr(newwidget, receiver)
                sender.connect(receiver)

        for i in reversed(range(self.catalogmodel.rowCount(), self.count())):
            self.removeTab(i)

    def setWidgetClass(self, cls):
        self.widgetcls = cls

    def currentCatalog(self):
        return self.catalogmodel.item(self.currentIndex()).data(Qt.UserRole)

    def currentHeader(self):
        return self.catalogmodel.item(self.currentIndex()).header
        warn(DeprecationWarning())

    def closeTab(self, i):
        newindex = self.currentIndex()
        if i <= self.currentIndex():
            newindex -= 1

        self.removeTab(i)
        self.catalogmodel.removeRow(i)
        self.selectionmodel.setCurrentIndex(self.catalogmodel.index(newindex, 0), QItemSelectionModel.Rows)


class TabViewSynchronizer(QObject):
    def __init__(self, tabviews: List[TabView]):
        super(TabViewSynchronizer, self).__init__()
        self.tabviews = tabviews
        for tabview in tabviews:
            tabview.currentChanged.connect(partial(self.sync, sourcetabview=tabview))
            tabview.tabCloseRequested.connect(partial(self.sync, sourcetabview=tabview))

    def sync(self, index, sourcetabview):
        for tabview in self.tabviews:
            if tabview is sourcetabview:
                continue
            tabview.setCurrentIndex(index)
            tabview.dataChanged(None, None)


class ContextMenuTabBar(QTabBar):
    def __init__(self):
        super(ContextMenuTabBar, self).__init__()
        self.contextMenu = QMenu()
        self.closeaction = QAction("&Close")
        self.closeaction.triggered.connect(self.close)
        self.closeothersaction = QAction("Close &Others")
        self.closeothersaction.triggered.connect(self.closeothers)
        self.closeallaction = QAction("Close &All")
        self.closeallaction.triggered.connect(self.closeall)
        self.contextMenu.addActions([self.closeaction, self.closeothersaction, self.closeallaction])
        self._rightclickedtab = None

    def close(self):
        self.tabCloseRequested.emit(self._rightclickedtab)

    def closeothers(self):
        for i in reversed(range(self.count())):
            if i != self._rightclickedtab:
                self.tabCloseRequested.emit(i)

    def closeall(self):
        for i in reversed(range(self.count())):
            self.tabCloseRequested.emit(i)

    def mousePressEvent(self, event: QMouseEvent):
        super(ContextMenuTabBar, self).mousePressEvent(event)
        self._rightclickedtab = self.tabAt(event.pos())
        if self._rightclickedtab != -1:
            if event.button() == Qt.RightButton:
                self.contextMenu.popup(self.mapToGlobal(event.pos()))


class TabItemSelectionModel(QItemSelectionModel):
    def __init__(self, tabview: TabView):
        super(TabItemSelectionModel, self).__init__(tabview.catalogmodel)
        self.tabview = tabview

    def currentIndex(self):
        return self.tabview.currentIndex()
