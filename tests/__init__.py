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
    splash = splash.XicamSplashScreen()
    mainloop()
