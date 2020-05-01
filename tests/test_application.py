import qtpy  # required unqused import to ensure that headless mode doesn't trigger :(
from xicam.run_xicam import _main
from pytestqt import qtbot
import sys


def test_application(qtbot):
    sys.argv = sys.argv[:1]
    main_window = _main([], exec=False)
    qtbot.addWidget(main_window)
    qtbot.waitForWindowShown(main_window)