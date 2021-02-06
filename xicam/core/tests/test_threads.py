from pytestqt import qtbot
import pytest
import os


@pytest.mark.skip(reason="thread module testing has issues")
def test_threads(qtbot):
    from xicam.core import threads
    from qtpy.QtCore import QObject, Signal


    def callback(a):
        assert a == 10

    t = threads.QThreadFuture(sum, [1, 2, 3, 4], callback_slot=callback)

    class Callback(QObject):
        sig = Signal(int)

    callback = Callback()
    t2 = threads.QThreadFuture(sum, [1, 2, 3, 4], callback_slot=callback.sig)

    t.start()
    t2.start()

    qtbot.waitSignals([t.sigFinished, t2.sigFinished])

@pytest.mark.skip(reason="thread module testing has issues")
def test_threads_iterator(qtbot):
    from xicam.core import threads

    results = []

    def callback(a):
        results.append(a)

    def testiterator():
        for i in range(3):
            yield i

    def check():
        assert sum(results) == 3

    t = threads.QThreadFutureIterator(testiterator, callback_slot=callback, finished_slot=check)
    t.start()
    qtbot.waitSignal(t.sigFinished)


@pytest.mark.skip(reason="thread module testing has issues")
def test_exit_before_thread(qtbot):
    from xicam.core import threads
    import time
    from qtpy.QtWidgets import QMainWindow

    window = QMainWindow()

    def long_thread():
        time.sleep(100000)

    for i in range(1000):
        t = threads.QThreadFuture(long_thread)

        t.start()
    time.sleep(.01)

    window.deleteLater()

@pytest.mark.skip(reason="thread module testing has issues")
def test_exit_before_decorated_thread(qtbot):
    from xicam.core import threads
    import time
    from qtpy.QtWidgets import QMainWindow

    window = QMainWindow()

    @threads.method()
    def long_thread():
        time.sleep(100000)

    for i in range(100):
        long_thread()

    time.sleep(.01)

    window.deleteLater()

@pytest.mark.skip(reason="thread module testing has issues")
def test_qthreads_and_pythreads(qtbot):
    from xicam.core import threads
    import time
    from qtpy.QtWidgets import QMainWindow

    window = QMainWindow()

    @threads.method()
    def long_thread():
        time.sleep(100000)

    for i in range(1000):
        long_thread()

    time.sleep(.01)

    window.deleteLater()
