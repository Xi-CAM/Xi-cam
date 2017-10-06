from qtpy.QtCore import *
from qtpy.QtGui import *
from qtpy.QtWidgets import *

from xicam.gui import static


class XicamSplashScreen(QSplashScreen):
    def __init__(self, mainwindow=QMainWindow, f=Qt.WindowStaysOnTopHint | Qt.SplashScreen):
        # self.pixmap = QPixmap(str(static.path('images/animated_logo.gif')))
        self.movie = QMovie(str(static.path('images/animated_logo.gif')))
        self.movie.frameChanged.connect(self.paintFrame)
        self.movie.jumpToFrame(1)
        pixmap = QPixmap(self.movie.frameRect().size())

        super(XicamSplashScreen, self).__init__(pixmap, f)

        self.timer = QTimer(self)
        self.timer.singleShot(1000, self.launchwindow)
        self.timer.singleShot(3000, self.hide)
        self._launching = False
        self.mainwindow = mainwindow
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setMask(pixmap.mask())
        self.show()
        self.raise_()
        self.activateWindow()
        QApplication.instance().setActiveWindow(self)

    def mousePressEvent(self, *args, **kwargs):
        self.timer.stop()
        self.launchwindow()

    def showEvent(self, event):
        self.movie.start()

    def hideEvent(self, event):
        self.movie.stop()

    def paintFrame(self):
        self.pixmap = self.movie.currentPixmap()
        self.setMask(self.pixmap.mask())
        self.setPixmap(self.pixmap)

    def sizeHint(self):
        return self.movie.scaledSize()

    def launchwindow(self):
        if not self._launching:
            self._launching = True

            app = QApplication.instance()
            self.mainwindow = self.mainwindow()
            self.timer.stop()

            self.mainwindow.show()
            self.mainwindow.raise_()
            self.mainwindow.activateWindow()
            app.setActiveWindow(self.mainwindow)
            self.hide()
            self.finish(self.mainwindow)
