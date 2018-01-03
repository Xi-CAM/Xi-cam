def test_msg():
    from .. import msg
    msg.logMessage('this', 'is', 'a', 'tests:', 42, level=msg.WARNING)


def test_threads():
    from xicam.gui import threads
    from qtpy.QtWidgets import QApplication
    from qtpy.QtCore import QTimer, QObject, Signal
    app = QApplication([])
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


# def test_data():
#     from .. import data
#     data.load_header(filenames='/home/rp/data/YL1031/YL1031__2m_00000.edf')

def test_lazyfield():
    import fabio
    from xicam.core.data import lazyfield
    class Handler(object):
        def __init__(self, path):
            self.path = path

        def __call__(self, *args, **kwargs):
            return fabio.open(self.path).data

    l = lazyfield(Handler, '/home/rp/data/YL1031/YL1031__2m_00000.edf')
    assert l.asarray()
