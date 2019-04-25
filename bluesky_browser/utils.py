from PyQt5.QtGui import QCursor, QDrag, QPixmap, QRegion
from PyQt5.QtWidgets import QWidget, QTabWidget
from PyQt5.QtCore import Qt, QMimeData, QPoint


class MoveableTabWidget(QTabWidget):
    """
    Adapted from https://stackoverflow.com/a/46719634/1221924
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setAcceptDrops(True)
        self.tabBar().setMouseTracking(True)
        self.indexTab = None
        self.setMovable(True)

    def mouseMoveEvent(self, e):
        if e.buttons() != Qt.RightButton:
            return

        globalPos = self.mapToGlobal(e.pos())
        tabBar = self.tabBar()
        posInTab = tabBar.mapFromGlobal(globalPos)
        self.indexTab = tabBar.tabAt(e.pos())
        tabRect = tabBar.tabRect(self.indexTab)

        pixmap = QPixmap(tabRect.size())
        tabBar.render(pixmap, QPoint(), QRegion(tabRect))
        mimeData = QMimeData()
        drag = QDrag(tabBar)
        drag.setMimeData(mimeData)
        drag.setPixmap(pixmap)
        cursor = QCursor(Qt.OpenHandCursor)
        drag.setHotSpot(e.pos() - posInTab)
        drag.setDragCursor(cursor.pixmap(), Qt.MoveAction)
        drag.exec_(Qt.MoveAction)

    def dragEnterEvent(self, e):
        e.accept()
        if e.source().parentWidget() != self:
            return

        # print(self.indexOf(self.widget(self.indexTab)))
        self.parent().tab_index = self.indexOf(self.widget(self.indexTab))

    def dragLeaveEvent(self, e):
        e.accept()

    def dropEvent(self, e):
        if e.source().parentWidget() == self:
            return

        e.setDropAction(Qt.MoveAction)
        e.accept()
        counter = self.count()

        if counter == 0:
            self.addTab(e.source().parentWidget().widget(self.parent().tab_index),
                        e.source().tabText(self.parent().tab_index))
        else:
            self.insertTab(counter + 1,
                           e.source().parentWidget().widget(self.parent().tab_index),
                           e.source().tabText(self.parent().tab_index))


class MoveableTabContainer(QWidget):
    """
    Adapted from https://stackoverflow.com/a/46719634/1221924
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.tab_index = 0
        self.moveWidget = None  # not needed?
