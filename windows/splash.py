import logging
from typing import Callable

from qtpy.QtCore import *
from qtpy.QtGui import *
from qtpy.QtWidgets import *

from xicam.gui import static


class XicamSplashScreen(QSplashScreen):
    def __init__(self, mainwindow: Callable[[], QMainWindow],
                 f: int = Qt.WindowStaysOnTopHint | Qt.SplashScreen):
        """
        A QSplashScreen customized to display an animated gif. The splash triggers launch when clicked.

        Parameters
        ----------
        mainwindow  :   class
            Subclass of QMainWindow to display after splashing
        f           :   int
            Extra flags (see base class)
        """
        # Start logging to the splash screen
        logging.getLogger().addHandler(self.showMessage)

        # Get logo movie from relative path
        self.movie = QMovie(str(static.path('images/animated_logo.gif')))

        # Setup drawing
        self.movie.frameChanged.connect(self.paintFrame)
        self.movie.jumpToFrame(1)
        self.pixmap = QPixmap(self.movie.frameRect().size())
        super(XicamSplashScreen, self).__init__(self.pixmap, f)
        self.setMask(self.pixmap.mask())

        # Setup timed triggers for launching the QMainWindow
        self.timer = QTimer(self)
        self.timer.singleShot(1000, self.launchwindow)
        self.timer.singleShot(3000, self.hide)
        self._launching = False
        self.mainwindow = mainwindow

        # Start splashing
        self.setAttribute(Qt.WA_DeleteOnClose)
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

            # Show the QMainWindow
            self.mainwindow.show()
            self.mainwindow.raise_()
            self.mainwindow.activateWindow()
            app.setActiveWindow(self.mainwindow)

            # Stop splashing
            self.hide()
            self.finish(self.mainwindow)
