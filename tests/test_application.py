from pytestqt import qtbot
from xicam.run_xicam import _main
import sys


def test_application(qtbot):
    sys.argv = sys.argv[:1]
    main_window = _main([], exec=False)
    qtbot.addWidget(main_window)
    qtbot.wait(6000)  # give it time to finish loading
    qtbot.waitForWindowShown(main_window)