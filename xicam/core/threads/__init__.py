import time
import sys
from functools import partial, wraps
from xicam.core import msg
import logging
from qtpy.QtCore import QTimer, Qt, Signal, QThread, QObject, QEvent, QCoreApplication
from qtpy.QtWidgets import QApplication
from qtpy.QtGui import QStandardItemModel, QColor, QStandardItem
import threading

log = msg.logMessage
log_error = msg.logError
show_busy = msg.showBusy
show_ready = msg.showReady


class ThreadManager(QStandardItemModel):
    """
    A global thread manager that holds on to threads with 'keepalive'
    """

    ThreadRole = Qt.UserRole

    def __init__(self):
        super(ThreadManager, self).__init__()
        self.timer = QTimer()
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self.update)
        self.timer.start()
        self._threads = []

    @property
    def threads(self):
        return self._threads

    def update(self):
        # purge
        for i in reversed(range(self.rowCount())):
            item = self.item(i)
            thread = item.data(self.ThreadRole)
            if thread._purge:
                self.removeRow(i)
                self._threads.remove(thread)
                continue
            elif thread.done or thread.cancelled or thread.exception:
                thread._purge = True

            if thread.exception:
                item.setData(QColor(Qt.red), Qt.ForegroundRole)
            elif thread.cancelled:
                item.setData(QColor(Qt.magenta), Qt.ForegroundRole)
            elif thread.done:
                item.setData(QColor(Qt.green), Qt.ForegroundRole)
            elif thread.running:
                item.setData(QColor(Qt.yellow), Qt.ForegroundRole)

    def append(self, thread):
        item = QStandardItem(repr(thread.method))
        item.setData(thread, role=self.ThreadRole)
        self.appendRow(item)
        self._threads.append(thread)


manager = ThreadManager()


# Justification for subclassing qthread: https://woboq.com/blog/qthread-you-were-not-doing-so-wrong.html
class QThreadFuture(QThread):
    """
    A future-like QThread, with many conveniences.
    """

    sigCallback = Signal()
    sigFinished = Signal()
    sigExcept = Signal(Exception)

    def __init__(
        self,
        method,
        *args,
        callback_slot=None,
        finished_slot=None,
        except_slot=None,
        default_exhandle=True,
        lock=None,
        threadkey: str = None,
        showBusy=True,
        keepalive=True,
        cancelIfRunning=True,
        priority=QThread.InheritPriority,
        timeout=0,
        **kwargs,
    ):
        super(QThreadFuture, self).__init__()

        # Auto-Kill other threads with same threadkey
        if threadkey and cancelIfRunning:
            for thread in manager.threads:
                if thread.threadkey == threadkey:
                    thread.cancel()
        self.threadkey = threadkey

        self.callback_slot = callback_slot
        self.except_slot = except_slot
        # if callback_slot: self.sigCallback.connect(callback_slot)
        if finished_slot:
            self.sigFinished.connect(finished_slot)
        if except_slot:
            self.sigExcept.connect(except_slot)
        if QApplication.instance():
            QApplication.instance().aboutToQuit.connect(self.quit)
        self.method = method
        self.args = args
        self.kwargs = kwargs
        self.timeout = timeout  # ms

        self.cancelled = False
        self.exception = None
        self._purge = False
        self.thread = None
        self.priority = priority
        self.showBusy = showBusy

        if keepalive:
            manager.append(self)

    @property
    def done(self):
        return self.isFinished()

    @property
    def running(self):
        return self.isRunning()

    def start(self):
        """
        Starts the thread
        """
        if self.running:
            raise ValueError("Thread could not be started; it is already running.")
        super(QThreadFuture, self).start(self.priority)
        if self.timeout:
            self._timeout_timer = QTimer.singleShot(self.timeout, self.cancel)

    def run(self, *args, **kwargs):
        """
        Do not call this from the main thread; you're probably looking for start()
        """
        if self.threadkey:
            threading.current_thread().name = self.threadkey
        self.cancelled = False
        self.exception = None
        if self.showBusy:
            show_busy()
        try:
            for self._result in self._run(*args, **kwargs):
                if not isinstance(self._result, tuple):
                    self._result = (self._result,)
                if self.callback_slot:
                    invoke_in_main_thread(self.callback_slot, *self._result)

        except Exception as ex:
            self.exception = ex
            self.sigExcept.emit(ex)
            log(
                f"Error in thread: "
                f'Method: {getattr(self.method, "__name__", "UNKNOWN")}\n'
                f"Args: {self.args}\n"
                f"Kwargs: {self.kwargs}",
                level=logging.ERROR,
            )
            log_error(ex)
        else:
            self.sigFinished.emit()
        finally:
            if self.showBusy:
                show_ready()
            self.quit()
            if QApplication.instance():
                try:
                    QApplication.instance().aboutToQuit.disconnect(self.quit)
                # Somehow the application never had its aboutToQuit connected to quit...
                except TypeError as e:
                    msg.logError(e)

    def _run(self, *args, **kwargs):  # Used to generalize to QThreadFutureIterator
        yield self.method(*self.args, **self.kwargs)

    def result(self):
        if not self.running:
            self.start()
        while not self.done and not self.exception:
            time.sleep(0.01)
        if self.exception:
            return self.exception
        return self._result

    def cancel(self):
        self.cancelled = True
        if self.except_slot:
            invoke_in_main_thread(self.except_slot, InterruptedError("Thread cancelled."))
        self.quit()
        self.wait()


class QThreadFutureIterator(QThreadFuture):
    """
    Same as QThreadFuture, but emits to the callback_slot for every yielded value of a generator
    """

    def _run(self, *args, **kwargs):
        yield from self.method(*self.args, **self.kwargs)


class InvokeEvent(QEvent):
    """
    Generic callable containing QEvent
    """

    EVENT_TYPE = QEvent.Type(QEvent.registerEventType())

    def __init__(self, fn, *args, **kwargs):
        QEvent.__init__(self, InvokeEvent.EVENT_TYPE)
        self.fn = fn
        self.args = args
        self.kwargs = kwargs


class Invoker(QObject):
    def event(self, event):
        try:
            if hasattr(event.fn, "signal"):  # check if invoking a signal or a callable
                event.fn.emit(*event.args, *event.kwargs.values())
            else:
                event.fn(*event.args, **event.kwargs)
            return True
        except Exception as ex:
            log("QThreadFuture callback could not be invoked.", level=logging.ERROR)
            log_error(ex)
        return False


_invoker = Invoker()


def invoke_in_main_thread(fn, *args, force_event=False, **kwargs):
    """
    Invoke a callable in the main thread. Use this for making callbacks to the gui where signals are inconvenient.
    """
    # co_name = sys._getframe().f_back.f_code.co_name
    # msg.logMessage(f"Invoking {fn} in main thread from {co_name}")

    if not force_event and is_main_thread():
        # we're already in the main thread; just do it!
        fn(*args, **kwargs)
    else:
        QCoreApplication.postEvent(_invoker, InvokeEvent(fn, *args, **kwargs))


def invoke_as_event(fn, *args, **kwargs):
    """Invoke a callable as an event in the main thread."""
    # co_name = sys._getframe().f_back.f_code.co_name
    # msg.logMessage(f"Invoking {fn} in main thread from {co_name}")
    invoke_in_main_thread(fn, *args, force_event=True, **kwargs)


def is_main_thread():
    return threading.current_thread() is threading.main_thread()


def method(
    callback_slot=None,
    finished_slot=None,
    except_slot=None,
    default_exhandle=True,
    lock=None,
    threadkey: str = None,
    showBusy=True,
    priority=QThread.InheritPriority,
    keepalive=True,
    cancelIfRunning=True,
    timeout=0,
    block=False,
):
    """
    Decorator for functions/methods to run as RunnableMethods on background QT threads
    Use it as any python decorator to decorate a function with @decorator syntax or at runtime:
    decorated_method = threads.method(callback_slot, ...)(method_to_decorate)
    then simply run it: decorated_method(*args, **kwargs)
    Parameters
    ----------
    callback_slot : function
        Function/method to run on a background thread
    finished_slot : QtCore.Slot
        Slot to call with the return value of the function
    except_slot : QtCore.Slot
        Function object (qt slot), slot to receive exception type, instance and traceback object
    default_exhandle : bool
        Flag to use the default exception handle slot. If false it will not be called
    lock : mutex/semaphore
        Simple lock if multiple access needs to be prevented
    Returns
    -------
    wrap_runnable_method : function
        Decorated function/method
    """

    def wrap_runnable_method(func):
        @wraps(func)
        def _runnable_method(*args, **kwargs):
            future = QThreadFuture(
                func,
                *args,
                callback_slot=callback_slot,
                finished_slot=finished_slot,
                except_slot=except_slot,
                default_exhandle=default_exhandle,
                lock=lock,
                threadkey=threadkey,
                showBusy=showBusy,
                priority=priority,
                keepalive=keepalive,
                cancelIfRunning=cancelIfRunning,
                timeout=timeout,
                **kwargs,
            )
            future.start()
            if block:
                future.result()
            return future

        return _runnable_method

    return wrap_runnable_method


def iterator(
    callback_slot=None,
    finished_slot=None,
    interrupt_signal=None,
    except_slot=None,
    default_exhandle=True,
    lock=None,
    threadkey: str = None,
    showBusy=True,
    priority=QThread.InheritPriority,
    keepalive=True,
):
    """
    Decorator for iterators/generators to run as RunnableIterators on background QT threads
    Use it as any python decorator to decorate a function with @decorator syntax or at runtime:
    decorated_iterator = threads.iterator(callback_slot, ...)(iterator_to_decorate).
    then simply run it: decorated_iterator(*args, **kwargs)

    Parameters
    ----------
    callback_slot : function
        Function/method to run on a background thread
    finished_slot : QtCore.Slot
        Slot to call with the return value of the function
    interrupt_signal : QtCore.Signal
        Signal to break out of iterator loop prematurely
    except_slot : QtCore.Slot
        Function object (qt slot), slot to receive exception type, instance and traceback object
    lock : mutex/semaphore
        Simple lock if multiple access needs to be prevented

    Returns
    -------
    wrap_runnable_iterator : function
        Decorated iterator/generator
    """

    def wrap_runnable_method(func):
        @wraps(func)
        def _runnable_method(*args, **kwargs):
            future = QThreadFutureIterator(
                func,
                *args,
                callback_slot=callback_slot,
                finished_slot=finished_slot,
                except_slot=except_slot,
                default_exhandle=default_exhandle,
                lock=lock,
                threadkey=threadkey,
                showBusy=showBusy,
                priority=priority,
                keepalive=keepalive,
                **kwargs,
            )
            future.start()

        return _runnable_method

    return wrap_runnable_method
