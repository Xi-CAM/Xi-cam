import pytest


@pytest.yield_fixture(autouse=True)
def with_QApplication():
    # Code that will run before your test
    from qtpy.QtWidgets import QApplication
    app = QApplication([])
    # A test function will be run at this point
    yield
    # Code that will run after your test, for example:
    # ... do something to check the existing files
    assert QApplication.exec_() == 0

def test_threads():
    from qtpy.QtWidgets import QApplication
    app = QApplication([])
    from xicam.gui import threads
    from qtpy.QtCore import QTimer, QObject, Signal
    q = QTimer()

    def callback(a):
        assert a == 10

    t = threads.QThreadFuture(sum, [1, 2, 3, 4], callback_slot=callback)

    class Callback(QObject):
        sig = Signal(int)

    callback = Callback()
    t2 = threads.QThreadFuture(sum, [1, 2, 3, 4], callback_slot=callback.sig)

    q.singleShot(1000, t.start)
    q.singleShot(1000, t2.start)
    q.singleShot(2000, app.quit)
    app.exec_()
