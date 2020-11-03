from pytestqt import qtbot
import pytest
import time
import os

from qtpy.QtCore import QObject, Signal
from xicam.core import threads
from qtpy.QtWidgets import QMainWindow


def test_threads(qtbot):

    def callback(a):
        assert a == 10

    t = threads.QThreadFuture(sum, [1, 2, 3, 4], callback_slot=callback)

    class Callback(QObject):
        sig = Signal(int)

    callback = Callback()

    # The callback sig here causes a seg fault
    #t2 = threads.QThreadFuture(sum, [1, 2, 3, 4], callback_slot=callback.sig)

    t.start()
    #t2.start()

    #qtbot.waitSignals([t.sigFinished, t2.sigFinished])
    qtbot.waitSignals([t.sigFinished])

def test_threads_iterator(qtbot):
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


def test_exit_before_thread(qtbot):
    window = QMainWindow()

    def long_thread():
        time.sleep(100000)

    for i in range(50):
        t = threads.QThreadFuture(long_thread)

        t.start()
    time.sleep(.01)

    window.deleteLater()

def test_exit_before_decorated_thread(qtbot):
    window = QMainWindow()

    @threads.method()
    def long_thread():
        time.sleep(100000)

    for i in range(50):
        long_thread()

    time.sleep(.01)

    window.deleteLater()

def test_qthreads_and_pythreads(qtbot):
    window = QMainWindow()

    @threads.method()
    def long_thread():
        time.sleep(100000)

    for i in range(50):
        long_thread()

    time.sleep(.01)

    window.deleteLater()
