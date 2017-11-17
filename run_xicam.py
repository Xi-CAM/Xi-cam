import sys

import qtpy
from qtpy.QtWidgets import *

if qtpy.API_NAME == 'PyQt4': del sys.modules['PySide']

def main():
    app = QApplication([])

    from xicam.gui.windows import splash

    splash = splash.XicamSplashScreen()
    app.exec_()


if __name__ == '__main__':
    main()
