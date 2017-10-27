from qtpy.QtWidgets import *

from xicam.gui.windows import splash
from xicam.gui.windows.mainwindow import XicamMainWindow


def makeapp():
    app = QApplication([])
    return app


def mainloop():
    app = QApplication.instance()
    app.exec_()


app = makeapp()
splash = splash.XicamSplashScreen(XicamMainWindow)
mainloop()
