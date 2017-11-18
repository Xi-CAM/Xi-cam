def test_msg():
    from .. import msg
    msg.logMessage('this', 'is', 'a', 'tests:', 42, level=msg.WARNING)


def test_threads():
    from xicam.core import threading
    from qtpy.QtWidgets import QApplication
    from qtpy.QtCore import QTimer, QObject, Signal
    app = QApplication([])

    def callback(a):
        assert a == 10

    q = QTimer()

    class Callback(QObject):
        sig = Signal(int)

    callback = Callback()
    t2 = threading.QThreadFuture(sum, [1, 2, 3, 4], callback_slot=callback.sig)

    q.singleShot(1000, t.start)
    q.singleShot(1000, t2.start)
    q.singleShot(2000, app.quit)
    app.exec_()
