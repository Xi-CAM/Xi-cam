import time
from functools import partial
from xicam.core import msg

from qtpy.QtCore import *


class ThreadManager(QObject):
    sigStateChanged = Signal()

    def __init__(self):
        super(ThreadManager, self).__init__()
        self._threads = []

    @property
    def threads(self):
        self.purge()
        return self._threads

    def purge(self):
        self._threads = [thread for thread in self._threads if not thread.purge]
        for thread in self._threads:
            if thread.done or thread.cancelled or thread.exception:
                thread.purge = True

    def append(self, thread):
        self._threads.append(thread)


manager = ThreadManager()


class QThreadFuture(QObject):
    sigCallback = Signal()
    sigFinished = Signal()
    sigExcept = Signal(Exception)

    def __init__(self, method, *args, callback_slot=None, finished_slot=None, except_slot=None, default_exhandle=True,
                 lock=None, **kwargs):
        super(QThreadFuture, self).__init__()

        self.callback_slot = callback_slot
        # if callback_slot: self.sigCallback.connect(callback_slot)
        if finished_slot: self.sigFinished.connect(finished_slot)
        if except_slot: self.sigExcept.connect(except_slot)
        self.method = method
        self.args = args
        self.kwargs = kwargs

        self.cancelled = False
        self.running = False
        self.done = False
        self.exception = None
        self.purge = False

        manager.append(self)

    def start(self):
        self.thread = QThread()
        self.thread.run = partial(self.run, *self.args, **self.kwargs)
        self.thread.start()

    def run(self, *args, **kwargs):
        self.cancelled = False
        self.running = True
        self.done = False
        self.exception = None
        try:
            self._result = self.method(*self.args, **self.kwargs)
            self.running = False
            if not isinstance(self._result, tuple): self._result = (self._result,)
            if self.callback_slot: invoke_in_main_thread(self.callback_slot, *self._result)
        except Exception as ex:
            self.exception = ex
            self.sigExcept.emit(ex)
            msg.logMessage(f'Error in thread: '
                           f'Method: {self.__repr__}\n'
                           f'Args: {self.args}\n'
                           f'Kwargs: {self.kwargs}', level=msg.ERROR)
            msg.logError(ex)
        else:
            self.done = True
            self.sigFinished.emit()

    def result(self):
        while not self.done and not self.exception:
            time.sleep(100)
        if self.exception: return self.exception
        return self.result

    def cancel(self):
        self.thread.terminate()
        self.cancelled = True


class InvokeEvent(QEvent):
    EVENT_TYPE = QEvent.Type(QEvent.registerEventType())

    def __init__(self, fn, *args, **kwargs):
        QEvent.__init__(self, InvokeEvent.EVENT_TYPE)
        self.fn = fn
        self.args = args
        self.kwargs = kwargs


class Invoker(QObject):
    def event(self, event):
        if hasattr(event.fn, 'signal'):  # check if invoking a signal or a callable
            event.fn.emit(*event.args, *event.kwargs.values())
        else:
            event.fn(*event.args, **event.kwargs)
        return True


_invoker = Invoker()


def invoke_in_main_thread(fn, *args, **kwargs):
    # print 'attempt invoke:',fn,args,kwargs
    QCoreApplication.postEvent(_invoker,
                               InvokeEvent(fn, *args, **kwargs))
