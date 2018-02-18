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


def test_threads_iterator():
    from qtpy.QtWidgets import QApplication
    app = QApplication([])
    from xicam.gui import threads
    from qtpy.QtCore import QTimer, QObject, Signal
    q = QTimer()

    results = []

    def callback(a):
        results.append(a)

    def testiterator():
        for i in range(3):
            yield i

    def check():
        assert sum(results) == 3

    t = threads.QThreadFutureIterator(testiterator, callback_slot=callback, finished_slot=check)

    q.singleShot(1000, t.start)
    q.singleShot(2000, app.quit)

    app.exec_()
