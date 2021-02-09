from qtpy.QtCore import Qt
from qtpy.QtWidgets import QWidget, QLabel, QPushButton
from pytestqt import qtbot


class HelloWidget(QWidget):
    def __init__(self, parent=None):
        super(HelloWidget, self).__init__(parent)
        self.greet_label = QLabel()
        self.button_greet = QPushButton("Greet")
        self.button_greet.clicked.connect(self.greet_clicked)

    def greet_clicked(self, *args):
        self.greet_label.setText("Hello!")


def test_hello(qtbot):
    widget = HelloWidget()
    qtbot.addWidget(widget)

    # click in the Greet button and make sure it updates the appropriate label
    qtbot.mouseClick(widget.button_greet, Qt.LeftButton)

    assert widget.greet_label.text() == "Hello!"
