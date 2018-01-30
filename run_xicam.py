import sys

import qtpy
from qtpy.QtWidgets import *
from qtpy.QtCore import *

if qtpy.API_NAME == 'PyQt5' and 'PySide' in sys.modules: del sys.modules['PySide']

QCoreApplication.setOrganizationName("Camera")
QCoreApplication.setApplicationName("Xi-cam")
try:
    QSettings().allKeys()
except Exception:
    QSettings().allKeys()

def main():
    app = QApplication([])

    from xicam.gui.windows import splash

    splash = splash.XicamSplashScreen()
    app.exec_()


if __name__ == '__main__':
    main()
