from pytest import fixture
from qtpy.QtWidgets import QApplication
from xicam.gui.widgets.debugmenubar import MouseDebugger
from pytestqt import qtbot


@fixture
def widget_debugger(qtbot):
    mousedebugger = MouseDebugger()
    QApplication.instance().installEventFilter(mousedebugger)
    qtbot.stopForInteraction()