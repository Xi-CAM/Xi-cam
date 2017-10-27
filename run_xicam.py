from qtpy.QtWidgets import *

app = QApplication([])

from xicam.gui.windows import splash

splash = splash.XicamSplashScreen()
app.exec_()
