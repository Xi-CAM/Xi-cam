import sys
import os
import signal
import trace
from xicam.core.args import parse_args

print("args:", sys.argv)
print("path:", sys.path)

if sys.argv[0].endswith("Xi-cam"):
    root = os.path.dirname(sys.argv[0])
    sys.path = [path for path in sys.path if os.path.abspath(root) in os.path.abspath(path)]

# Quickly extract zip file to make imports easier
if ".zip/" in os.__file__:
    import zipfile

    zip_ref = zipfile.ZipFile(os.path.dirname(os.__file__), "r")
    zip_ref.extractall(os.path.dirname(os.path.dirname(os.__file__)))
    zip_ref.close()

os.environ["QT_API"] = "pyqt5"
import qtpy
from qtpy.QtWidgets import QApplication, QErrorMessage
from qtpy.QtCore import QCoreApplication, QProcess

if qtpy.API_NAME == "PyQt5" and "PySide" in sys.modules:
    del sys.modules["PySide"]

QCoreApplication.setOrganizationName("Camera")
QCoreApplication.setApplicationName("Xi-cam")


def _main(args, exec=True):
    # import pydm
    # app = QApplication([])
    # app = pydm.PyDMApplication()
    app = QApplication.instance() or QApplication([])
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    from xicam.gui.windows import splash
    from xicam.core import msg

    if getattr(args, 'verbose', False):
        QErrorMessage.qtHandler()

    # start splash in subprocess
    splash_proc = QProcess()
    # splash_proc.started.connect(lambda: print('started splash'))
    # splash_proc.finished.connect(lambda: print('finished splashing'))
    log_file = msg.file_handler.baseFilename
    initial_length = os.path.getsize(log_file)
    splash_proc.start(sys.executable, [splash.__file__, log_file, str(initial_length)])

    from xicam.gui.windows.mainwindow import XicamMainWindow

    mainwindow = XicamMainWindow()
    while splash_proc.state() != QProcess.NotRunning:
        app.processEvents()
    # splash_proc.waitForFinished()
    mainwindow.show()
    mainwindow.activateWindow()

    # splash = splash.XicamSplashScreen(args=args)
    if exec:
        return app.exec_()
    else:
        return mainwindow


def main():
    args = parse_args(exit_on_fail=True)
    if args.verbose > 1:
        tracer = trace.Trace(count=False, trace=True)
        tracer.run("_main(args)")
    else:
        return _main(args)


if __name__ == "__main__":
    return_code = main()
    sys.exit(return_code)
# TODO: check entry log when running entry point
