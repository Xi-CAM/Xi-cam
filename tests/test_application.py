import pytest
from pytestqt import qtbot
from xicam.run_xicam import _main
import sys


@pytest.mark.skipif(sys.platform == "win32", reason="splash hangs on windows")
@pytest.mark.skip(reason="see comment below")
#tests/test_application.py /home/travis/.travis/functions: line 109:  6332 Aborted    
def test_application(qtbot):
    sys.argv = sys.argv[:1]
    main_window = _main([], exec=False)
    qtbot.addWidget(main_window)
    qtbot.wait(6000)  # give it time to finish loading
    qtbot.waitForWindowShown(main_window)
