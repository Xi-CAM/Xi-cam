from pytestqt import qtbot
from xicam.gui.windows.mainwindow import XicamMainWindow


def test_application(qtbot):
    window = XicamMainWindow()
    qtbot.addWidget(window)
    qtbot.waitForWindowShown(window)  # give it time to finish loading