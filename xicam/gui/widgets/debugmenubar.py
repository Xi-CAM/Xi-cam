import sys

from qtpy.QtWidgets import QMenuBar, QShortcut, QMenu, QPushButton, QApplication, QWidget
from qtpy.QtGui import QKeySequence
from qtpy.QtCore import Qt, QObject, QEvent

# Hack to work around PySide being imported from nowhere:
import qtpy

if "PySide.QtCore" in sys.modules and qtpy.API != "pyside":
    del sys.modules["PySide.QtCore"]

from qtconsole.rich_jupyter_widget import RichJupyterWidget
from qtconsole.inprocess import QtInProcessKernelManager

from xicam.plugins import manager as plugin_manager


class DebuggableMenuBar(QMenuBar):
    def __init__(self, *args, **kwargs):
        super(DebuggableMenuBar, self).__init__(*args, **kwargs)

        self.debugshortcut = QShortcut(QKeySequence("Ctrl+Return"), self, self.showDebugMenu, context=Qt.ApplicationShortcut)

        self._debugmenu = QMenu("Debugging")
        self._debugmenu.addAction("Debug widget", self.startDebugging)
        self._debugmenu.addAction("Hot-reload", plugin_manager.hot_reload)

        self.mousedebugger = MouseDebugger()

    def showDebugMenu(self):
        self.addMenu(self._debugmenu)

    def startDebugging(self):
        QApplication.instance().installEventFilter(self.mousedebugger)


class MouseDebugger(QObject):
    def eventFilter(self, obj, event):
        # print(event,obj)
        # print(self.sender())
        if event.type() == QEvent.MouseButtonPress:
            print(QApplication.instance().activeWindow().childAt(event.pos()))
            IPythonDebugger(QApplication.instance().activeWindow().childAt(event.pos())).show()
            QApplication.instance().removeEventFilter(self)
            return True
        return False


class IPythonDebugger(RichJupyterWidget):
    def __init__(self, widget: QWidget):
        super(IPythonDebugger, self).__init__()

        # Setup the kernel
        self.kernel_manager = QtInProcessKernelManager()
        self.kernel_manager.start_kernel()
        kernel = self.kernel_manager.kernel
        kernel.gui = "qt"

        # Push QWidget to the console
        kernel.shell.push({"widget": widget})

        self.kernel_client = self.kernel_manager.client()
        self.kernel_client.start_channels()

        # Setup console widget
        def stop():
            self.kernel_client.stop_channels()
            self.kernel_manager.shutdown_kernel()

        self.exit_requested.connect(stop)


if __name__ == "__main__":
    from qtpy.QtWidgets import QApplication, QMainWindow, QLabel

    app = QApplication([])
    window = QMainWindow()
    window.setCentralWidget(QLabel("test"))
    db = DebuggableMenuBar()
    window.setMenuBar(db)
    window.show()

    app.exec_()
