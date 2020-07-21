from argparse import Namespace
from pytestqt import qtbot
from xicam.run_xicam import _main
import pytest
import sys
# from qtpy import API_NAME


def test_application(qtbot):
    sys.argv = sys.argv[:1]
    main_window = _main(Namespace(nosplash=True), exec=False)
    qtbot.addWidget(main_window)
    print()  # this prevents Windows access violation err in test...
    # if API_NAME.lower() == "pyside2":
    qtbot.wait(6000)  # give it time to finish loading
    qtbot.waitForWindowShown(main_window)
    # else:
    #     qtbot.waitExposed(main_window, 10000)