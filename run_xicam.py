import sys
import os

import trace



print('args:', sys.argv)
print('path:', sys.path)
if sys.argv[0].endswith('Xi-cam'):
    root = os.path.dirname(sys.argv[0])
    sys.path = [path for path in sys.path if os.path.abspath(root) in os.path.abspath(path)]

# Quickly extract zip file to make imports easier
if '.zip/' in os.__file__:
    import zipfile

    zip_ref = zipfile.ZipFile(os.path.dirname(os.__file__), 'r')
    zip_ref.extractall(os.path.dirname(os.path.dirname(os.__file__)))
    zip_ref.close()

os.environ['QT_API'] = 'pyqt5'
import qtpy
from qtpy.QtWidgets import *
from qtpy.QtCore import *

if qtpy.API_NAME == 'PyQt5' and 'PySide' in sys.modules: del sys.modules['PySide']

QCoreApplication.setOrganizationName("Camera")
QCoreApplication.setApplicationName("Xi-cam")

def main():
    # import pydm
    # app = QApplication([])
    # app = pydm.PyDMApplication()
    app = QApplication([])

    from xicam.gui.windows import splash

    if '-v' in sys.argv:
        QErrorMessage.qtHandler()

    from xicam.gui.windows.mainwindow import XicamMainWindow
    splash = splash.XicamSplashScreen()

    def start():
        mainwindow = XicamMainWindow()
        splash.mainwindow = mainwindow
        mainwindow.load()

    # Start loading the mainwindow within Qt mainloop
    QTimer.singleShot(0, start)

    app.exec_()


if __name__ == '__main__':
    if '-v' in sys.argv:
        tracer = trace.Trace(count=False, trace=True)
        tracer.run('main()')
    else:
        main()

# TODO: check entry log when running entry point