"""This module provides application-wide logging tools.

Unhandled exceptions are hooked into the log. Messages and progress
can be displayed in the main Xi-cam window using showProgress and showMessage.

Constants
---------
DEFAULT_FILE_LOG_LEVEL : int
    Default logging level for logging to file.
DEFAULT_STREAM_LOG_LEVEL : int
    Default logging level for logging to stream (e.g. sys.stdout).
FILE_LOG_LEVEL_SETTINGS_NAME : str
    Name of the settings value for defining the file logging level.
LOGGING_SETTINGS_NAME : str
    Name of the serialized settings via LogginSettingsPlugin (in GUI mode).
STREAM_LOG_LEVEL_SETTINGS_NAME : str
    Name of the settings value for defining the stream logging level.

"""
import cloudpickle as pickle
import logging
import faulthandler
import sys
import os
import time
import warnings
from typing import Any
import traceback
from collections import defaultdict
from qtpy.QtCore import QSettings, QTimer
from xicam.core import paths
from contextlib import contextmanager


# TODO: Add logging for images
# TODO: Add icons in GUI reflection

# Log levels constants
DEBUG = logging.DEBUG  # 10
INFO = logging.INFO  # 20
WARNING = logging.WARNING  # 30
ERROR = logging.ERROR  # 40
CRITICAL = logging.CRITICAL  # 50

levels = {DEBUG: "DEBUG", INFO: "INFO", WARNING: "WARNING", ERROR: "ERROR", CRITICAL: "CRITICAL"}

# Define constants that the LoggingSettingsPlugin will end up using as well
DEFAULT_FILE_LOG_LEVEL = DEBUG
DEFAULT_STREAM_LOG_LEVEL = WARNING
FILE_LOG_LEVEL_SETTINGS_NAME = "File Log Level"
LOGGING_SETTINGS_NAME = "Logging"
STREAM_LOG_LEVEL_SETTINGS_NAME = "Terminal Log Level"

# GUI widgets are registered into these slots to display messages/progress
statusbar = None
progressbar = None

# Create a log file that captures all logs (DEBUG)
log_dir = os.path.join(paths.user_cache_dir, "logs")
os.makedirs(log_dir, exist_ok=True)
log_file = "out.log"
logger = logging.getLogger("xicam")
logger.setLevel("DEBUG")  # minimum level shown

# Create a formatter that all handlers below can use for formatting their log messages
# format = "%(asctime)s - %(name)s - %(module)s:%(lineno)d - %(funcName)s - "
format = "%(asctime)s - %(caller_name)s - %(levelname)s - %(threadName)s > %(message)s"
date_format = "%a %b %d %H:%M:%S %Y"
formatter = logging.Formatter(fmt=format, datefmt=date_format)

# Use the QSettings set up for us by LoggingSettingsPlugin
logging_settings = QSettings().value(LOGGING_SETTINGS_NAME, {})
if logging_settings:
    # Unserialize the bytes stream (gives us a dict)
    logging_settings = pickle.loads(logging_settings)
    # Since LoggingSettingsPlugin is a ParameterSettingsPlugin,
    # we access the settings (parameters) through the "children" key
    logging_settings = logging_settings.get("children", {})

# Create a file handler for logging to a file
file_log_level = DEFAULT_FILE_LOG_LEVEL
# See if we have the file logging level available to us
file_log_settings = logging_settings.get(FILE_LOG_LEVEL_SETTINGS_NAME, {}).get("value")
if logging_settings and file_log_settings:
    file_log_level = file_log_settings
# By default, append to log file
file_handler = logging.FileHandler(os.path.join(log_dir, log_file))
file_handler.setLevel(file_log_level)  # minimum level shown
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

# Create a stream handler (attaches to sys.stderr by default)
stream_log_level = DEFAULT_STREAM_LOG_LEVEL
# See if we have the stream logging level available to us
stream_log_settings = logging_settings.get(STREAM_LOG_LEVEL_SETTINGS_NAME, {}).get("value")
if logging_settings and stream_log_settings:
    stream_log_level = stream_log_settings
stream_handler = logging.StreamHandler()
stream_handler.setLevel(stream_log_level)  # minimum level shown
stream_handler.setFormatter(formatter)
logger.addHandler(stream_handler)

trayicon = None
if "qtpy" in sys.modules:
    from qtpy.QtWidgets import QApplication

    if QApplication.instance():
        from qtpy.QtWidgets import QSystemTrayIcon
        from qtpy.QtGui import QIcon, QPixmap
        from xicam.gui.static import path

        trayicon = QSystemTrayIcon(QIcon(QPixmap(str(path("icons/cpu.png")))))  # TODO: better icon

_thread_count = 0


def _increment_thread():
    global _thread_count
    _thread_count += 1
    return _thread_count


threadIds = defaultdict(_increment_thread)


def showProgress(value: int, minval: int = 0, maxval: int = 100):
    """
    Displays the progress value on the subscribed QProgressBar (set as the global progressbar)

    Parameters
    ----------
    value   : int
        Progress value.
    minval  : int
        Minimum value (default: 0)
    maxval  : int
        Maximum value (default: 100)

    """
    if progressbar:
        from .. import threads  # must be a late import

        threads.invoke_in_main_thread(progressbar.show)
        threads.invoke_in_main_thread(progressbar.setRange, minval, maxval)
        threads.invoke_in_main_thread(progressbar.setValue, value)


def showBusy():
    """
     Displays a busy indicator on the subscribed QProgressBar (set as the global progressbar)

    """
    if progressbar:
        from .. import threads  # must be a late import

        threads.invoke_in_main_thread(progressbar.show)
        threads.invoke_in_main_thread(progressbar.setRange, 0, 0)


def hideBusy():
    """
    Stops a busy indicator on the subscribed QProgressBar (set as the global progressbar)

    """
    if progressbar:
        from .. import threads  # must be a late import

        threads.invoke_in_main_thread(progressbar.hide)
        threads.invoke_in_main_thread(progressbar.setRange, 0, 100)


# aliases
showReady = hideBusy
hideProgress = hideBusy


def notifyMessage(*args, timeout=8000, title="", level: int = INFO):
    """
    Same as logMessage, but displays to the subscribed notification system with a timeout.

    Parameters
    ----------
    args        :   tuple(str)
        See logMessage...
    timeout     :   int
        How long the message is displayed. If set 0, the message is persistent.
    kwargs      :   dict
        See logMessage...
    Returns
    -------

    """
    global trayicon
    if trayicon:
        icon = None
        if level in [INFO, DEBUG]:
            icon = trayicon.Information
        if level == WARNING:
            icon = trayicon.Warning
        if level in [ERROR, CRITICAL]:
            icon = trayicon.Critical
        if icon is None:
            raise ValueError("Invalid message level.")
        from .. import threads  # must be a late import

        threads.invoke_in_main_thread(trayicon.show)

        threads.invoke_in_main_thread(trayicon.showMessage, title, "".join(args), icon, timeout)
        threads.invoke_in_main_thread(lambda *_: QTimer.singleShot(timeout, trayicon.hide))
        # trayicon.showMessage(title, ''.join(args), icon, timeout)  # TODO: check if title and message are swapped?

    logMessage(*args)


def showMessage(*args, timeout=5, **kwargs):
    """
    Same as logMessage, but displays to the subscribed statusbar with a timeout.

    Parameters
    ----------
    args        :   tuple(str)
        See logMessage...
    timeout     :   int
        How long the message is displayed. If set 0, the message is persistent.
    kwargs      :   dict
        See logMessage...
    Returns
    -------

    """
    s = " ".join(args)
    if statusbar is not None:
        from .. import threads  # must be a late import

        threads.invoke_in_main_thread(statusbar.showMessage, s, timeout * 1000)

    logMessage(*args, **kwargs)


def logMessage(*args: Any, level: int = INFO, loggername: str = None, sep=" "):
    """
    Logs messages to logging log. Gui widgets can be subscribed to the log with:
        logging.getLogger().addHandler(callable)


    Parameters
    ----------
    args            : tuple[str]
        Similar to python 3's print(), any number of objects that can be cast as str. These are joined and printed as
        one line.
    level           : int
        Logging level; one of msg.DEBUG, msg.INFO, msg.WARNING, msg.ERROR, msg.CRITICAL. Default is INFO
    loggername      : str
        The name of the log to post the message into. Typically left blank, and populated by inspection.
    sep             : str
        A string to use for joining args; the separator

    """

    # Join the args to a string
    message = sep.join(map(str, args))

    if loggername is not None:
        warnings.warn("Custom loggername is no longer supported, " "ignored.")
    caller_name = sys._getframe().f_back.f_code.co_name
    logger.log(level, message, extra={"caller_name": caller_name})


def clearMessage():
    """
    Clear messages from the statusbar
    """
    from .. import threads  # must be a late import

    threads.invoke_in_main_thread(statusbar.clearMessage)


def logError(exception: Exception, value=None, tb=None, **kwargs):
    """
    Logs an exception with traceback. All uncaught exceptions get hooked here

    """

    if not value:
        value = exception
    if not tb:
        tb = exception.__traceback__
    kwargs["level"] = ERROR
    if "loggername" not in kwargs:
        kwargs["loggername"] = sys._getframe().f_back.f_code.co_name
    logMessage("\n", "The following error was handled safely by Xi-cam. It is displayed here for debugging.", **kwargs)
    try:
        logMessage("\n", *traceback.format_exception(exception, value, tb), **kwargs)
    except AttributeError:
        logMessage("\n", *traceback.format_exception_only(exception, value), **kwargs)


cumulative_time = defaultdict(lambda: 0)


@contextmanager
def logTime(*args: Any, level: int = INFO, loggername: str = None, cumulative_key: str = "", sep=" ") -> None:
    start = time.clock_gettime_ns(time.CLOCK_THREAD_CPUTIME_ID)
    yield
    elapsed_time = time.clock_gettime_ns(time.CLOCK_THREAD_CPUTIME_ID) - start

    if cumulative_key:
        cumulative_time[cumulative_key] += elapsed_time
        extra_args = [
            f"cumulative elapsed: {cumulative_time[cumulative_key] / 1e6} ms elapsed: {elapsed_time / 1e6} ms elapsed"
        ]
    else:
        extra_args = [f"elapsed: {elapsed_time / 1e6} ms elapsed"]

    logMessage(*(args + extra_args), level, loggername, sep)


@contextmanager
def busyContext() -> None:
    showBusy()
    yield
    showReady()


import sys

sys._excepthook = sys.excepthook = logError

try:
    faulthandler.enable()
except RuntimeError:
    faulthandler.enable(file=open(os.path.join(paths.user_cache_dir, "logs", "crash_log.log"), "w"))

# The above enables printing tracebacks during hard crashes. To see it in action, try the following lines
# import ctypes
# ctypes.string_at(0)
