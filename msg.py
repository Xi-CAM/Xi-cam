import inspect
import logging
import sys
import time

# TODO: Add tests
# TODO: Add docs
# TODO: Add logging for images
# TODO: Add icons in GUI reflection

statusbar = None  # Must be registered to output to a ui status bar
progressbar = None

stdch = logging.StreamHandler(sys.stdout)

DEBUG = logging.DEBUG  # 10
INFO = logging.INFO  # 20
WARNING = logging.WARNING  # 30
ERROR = logging.ERROR  # 40
CRITICAL = logging.CRITICAL  # 50


def showProgress(value, min=0, max=100):
    if progressbar:
        progressbar.show()
        progressbar.setRange(min, max)
        progressbar.setValue(value)


def showBusy():
    if progressbar:
        progressbar.show()
        progressbar.setRange(0, 0)


def hideBusy():
    if progressbar:
        progressbar.hide()
        progressbar.setRange(0, 100)


# aliases
showReady = hideBusy
hideProgress = hideBusy


def showMessage(*args, timeout=0, **kwargs):
    s = ' '.join(args)
    if statusbar is not None:
        statusbar.showMessage(s, timeout * 1000)

    logMessage(s, **kwargs)


def logMessage(*args, level=INFO, loggername=None, timestamp=None, suppressreprint=False):
    s = ' '.join(map(str, args))

    # ATTENTION: loggername is 'intelligently' determined with inspect. You probably want to leave it None.
    if loggername is not None:
        loggername = inspect.stack()[1][3]
    logger = logging.getLogger(loggername)
    try:
        stdch.setLevel(level)
    except ValueError:
        level = logging.CRITICAL
        logger.log('Unrecognized logger level for following message...', level)

    logger.addHandler(stdch)

    if timestamp is None: timestamp = time.asctime()

    m = timestamp + '\t' + str(s)

    logger.log(level, m)

    try:
        if not suppressreprint: print(m)
    except UnicodeEncodeError:
        print('A unicode string could not be written to console. Some logging will not be displayed.')


def clearMessage():
    statusbar.clearMessage()
