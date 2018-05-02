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
                 lock=None, threadkey: str = None, showBusy=True, **kwargs):
        super(QThreadFuture, self).__init__()

        # Auto-Kill other threads with same threadkey
        if threadkey:
            for thread in manager.threads:
                if thread.threadkey == threadkey:
                    thread.cancel()
        self.threadkey = threadkey

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
        self.thread = None
        self.showBusy = showBusy

        manager.append(self)

    def start(self):
        if not self.thread:
            self.thread = QThread()
            self.thread.run = partial(self.run, *self.args, **self.kwargs)
            self.thread.start()
        else:
            raise ValueError('Thread could not be started; it is already running.')

    def run(self, *args, **kwargs):
        self.cancelled = False
        self.running = True
        self.done = False
        self.exception = None
        if self.showBusy: invoke_in_main_thread(msg.showBusy)
        try:
            for self._result in self._run(*args, **kwargs):
                if not isinstance(self._result, tuple): self._result = (self._result,)
                if self.callback_slot: invoke_in_main_thread(self.callback_slot, *self._result)
                self.running = False

        except Exception as ex:
            self.exception = ex
            self.sigExcept.emit(ex)
            msg.logMessage(f'Error in thread: '
                           f'Method: {self.method.__name__}\n'
                           f'Args: {self.args}\n'
                           f'Kwargs: {self.kwargs}', level=msg.ERROR)
            msg.logError(ex)
        else:
            self.done = True
            self.sigFinished.emit()
        finally:
            invoke_in_main_thread(msg.showReady)

    def _run(self, *args, **kwargs):
        yield self.method(*self.args, **self.kwargs)

    def result(self):
        while not self.done and not self.exception:
            time.sleep(.1)
        if self.exception: return self.exception
        return self._result

    def cancel(self):
        self.thread.quit()
        self.thread.wait()
        self.cancelled = True


class QThreadFutureIterator(QThreadFuture):
    def _run(self, *args, **kwargs):
        yield from self.method(*self.args, **self.kwargs)


class InvokeEvent(QEvent):
    EVENT_TYPE = QEvent.Type(QEvent.registerEventType())

    def __init__(self, fn, *args, **kwargs):
        QEvent.__init__(self, InvokeEvent.EVENT_TYPE)
        self.fn = fn
        self.args = args
        self.kwargs = kwargs


class Invoker(QObject):
    def event(self, event):
        try:
            if hasattr(event.fn, 'signal'):  # check if invoking a signal or a callable
                event.fn.emit(*event.args, *event.kwargs.values())
            else:
                event.fn(*event.args, **event.kwargs)
            return True
        except Exception as ex:
            msg.logMessage('QThreadFuture callback could not be invoked.', level=msg.ERROR)
            msg.logError(ex)
        return False


_invoker = Invoker()


def invoke_in_main_thread(fn, *args, **kwargs):
    # print 'attempt invoke:',fn,args,kwargs
    QCoreApplication.postEvent(_invoker,
                               InvokeEvent(fn, *args, **kwargs))
