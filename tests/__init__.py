from qtpy.QtCore import *
from qtpy.QtWidgets import *


def makeapp():
    app = QApplication([])
    return app


def mainloop():
    app = QApplication.instance()
    app.exec_()


def test_splash():
    from ..windows import splash
    app = makeapp()
    splash = splash.XicamSplashScreen(QMainWindow)
    mainloop()


def test_mainwindow():
    from ..windows.mainwindow import XicamMainWindow

    app = makeapp()
    window = XicamMainWindow()
    window.show()

    t = QTimer()
    # t.singleShot(1000, window.close)

    mainloop()