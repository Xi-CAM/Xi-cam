import qtpy  # required unqused import to ensure that headless mode doesn't trigger :(
from xicam.run_xicam import _main
from pytestqt import qtbot
import sys


def test_application(qtbot):
    sys.argv = sys.argv[:1]
    qtbot.addWidget(_main([], exec=False))
    qtbot.wait(10)  # give it time to finish loading
