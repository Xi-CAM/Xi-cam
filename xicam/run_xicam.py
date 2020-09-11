import sys
import os
import signal
import trace
import atexit
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
from qtpy.QtCore import QCoreApplication, QProcess, QTimer

if qtpy.API_NAME == "PyQt5" and "PySide" in sys.modules:
    del sys.modules["PySide"]
elif qtpy.API_NAME == "PySide2" and "PyQt5" in sys.modules:
    del sys.modules["PyQt5"]

QCoreApplication.setOrganizationName("Camera")
QCoreApplication.setApplicationName("Xi-cam")

mainwindow = None
splash_proc = None
show_check_timer = None


def check_show_mainwindow():
    if splash_proc and splash_proc.state() == QProcess.NotRunning and mainwindow:
        # splash_proc.waitForFinished()
        mainwindow.show()
        mainwindow.activateWindow()
        show_check_timer.stop()


def _main(args, exec=True):
    global mainwindow, splash_proc, show_check_timer
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

    show_check_timer = QTimer()
    show_check_timer.timeout.connect(check_show_mainwindow)
    show_check_timer.start(100)

    from xicam.gui.windows.mainwindow import XicamMainWindow

    mainwindow = XicamMainWindow()

    if exec:
        return app.exec_()
    else:
        return mainwindow


def main():
    args = parse_args(exit_on_fail=True)
    if args.verbose > 1:
        tracer = trace.Trace(count=False, trace=True)
        tracer.run(f"_main(None)")  # TODO: map args into main
    else:
        return _main(args)


def exit_checks():
    from xicam.core import msg
    import threading
    msg.logMessage('Background threads:', threading.active_count()-1)
    # msg.logMessage('Active background threads:', len([thread for thread in threading.enumerate() if not isinstance(thread, threading._DummyThread)])-1)
    msg.logMessage('Active background threads:',
                   len(list(filter(lambda thread: not isinstance(thread, threading._DummyThread),
                                   threading.enumerate())))-1)

    for thread in threading.enumerate():
        if thread is threading.current_thread() or isinstance(thread, threading._DummyThread):# or thread.daemon
            continue
        msg.logMessage('Waiting for thread:', thread.name)

        thread.join(timeout=3)
        msg.logError(TimeoutError(f'Thread named "{thread.name}" took too long to exit as Xi-CAM was closing. '
                                       # 'Please report this.')
        ))


atexit.register(exit_checks)


if __name__ == "__main__":
    return_code = main()
    sys.exit(return_code)
