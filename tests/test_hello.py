from qtpy import QtCore
from pytestqt import qtbot


def test_hello(qtbot):
    widget = HelloWidget()
    qtbot.addWidget(widget)

    # click in the Greet button and make sure it updates the appropriate label
    qtbot.mouseClick(widget.button_greet, QtCore.Qt.LeftButton)

    assert widget.greet_label.text() == "Hello!"
