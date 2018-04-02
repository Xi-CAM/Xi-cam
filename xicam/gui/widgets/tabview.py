from qtpy.QtWidgets import *
from qtpy.QtGui import *
from qtpy.QtCore import *
from typing import List
from functools import partial


class TabView(QTabWidget):
    def __init__(self, model=None, widgetcls=None, field=None, **kwargs):
        super(TabView, self).__init__()
        self.setTabBar(ContextMenuTabBar())
        self.kwargs = kwargs

        self.setWidgetClass(widgetcls)
        self.model = None
        self.selectionmodel = None  # type: TabItemSelectionModel
        if model: self.setModel(model)
        self.field = field

    def setModel(self, model: QStandardItemModel):
        self.model = model
        self.selectionmodel = TabItemSelectionModel(self)
        model.dataChanged.connect(self.dataChanged)
        self.tabCloseRequested.connect(self.closeTab)

        self.setTabsClosable(True)
        self.setDocumentMode(True)

    def dataChanged(self, start, end):
        for i in range(self.model.rowCount()):

            if self.widget(i):
                if self.widget(i).header == self.model.item(i).header:
                    continue
            self.setCurrentIndex(
                self.insertTab(i, self.widgetcls(self.model.item(i).header, self.field, **self.kwargs),
                               self.model.item(i).text()))

        for i in reversed(range(self.model.rowCount(), self.count())):
            self.removeTab(i)

    def setWidgetClass(self, cls):
        self.widgetcls = cls

    def currentHeader(self):
        return self.model.item(self.currentIndex())

    def closeTab(self, i):
        self.removeTab(i)
        self.model.removeRow(i)


class TabViewSynchronizer(QObject):
    def __init__(self, tabviews: List[TabView]):
        super(TabViewSynchronizer, self).__init__()
        self.tabviews = tabviews
        for tabview in tabviews:
            tabview.currentChanged.connect(partial(self.sync, sourcetabview=tabview))
            tabview.tabCloseRequested.connect(partial(self.sync, sourcetabview=tabview))

    def sync(self, index, sourcetabview):
        for tabview in self.tabviews:
            if tabview is sourcetabview: continue
            tabview.setCurrentIndex(index)
            tabview.dataChanged(None, None)


class ContextMenuTabBar(QTabBar):
    def __init__(self):
        super(ContextMenuTabBar, self).__init__()
        self.contextMenu = QMenu()
        self.closeaction = QAction('&Close')
        self.closeaction.triggered.connect(self.close)
        self.closeothersaction = QAction('Close &Others')
        self.closeothersaction.triggered.connect(self.closeothers)
        self.closeallaction = QAction('Close &All')
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
        super(TabItemSelectionModel, self).__init__(tabview.model)
        self.tabview = tabview

    def currentIndex(self):
        return self.tabview.currentIndex()
