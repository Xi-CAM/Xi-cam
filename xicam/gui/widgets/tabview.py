from qtpy.QtWidgets import *
from qtpy.QtGui import *
from qtpy.QtCore import *


class TabView(QTabWidget):
    def __init__(self, model=None, widgetcls=None, field=None):
        super(TabView, self).__init__()
        self.setTabBar(ContextMenuTabBar())

        self.setWidgetClass(widgetcls)
        self.model = None
        if model: self.setModel(model)
        self.field = field

    def setModel(self, model: QStandardItemModel):
        self.model = model
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
                self.insertTab(i, self.widgetcls(self.model.item(i).header, self.field), '????'))

        for i in reversed(range(self.model.rowCount(), self.count())):
            self.removeTab(i)

    def setWidgetClass(self, cls):
        self.widgetcls = cls

    def closeTab(self, i):
        self.removeTab(i)
        self.model.removeRow(i)


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
