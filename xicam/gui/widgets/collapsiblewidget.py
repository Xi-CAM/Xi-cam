from qtpy.QtCore import Signal
from qtpy.QtWidgets import QLabel, QVBoxLayout, QWidget


class CollapsibleWidget(QWidget):

    toggled = Signal(bool)

    def __init__(self, widget: QWidget, name: str, parent=None):
        super(CollapsibleWidget, self).__init__(parent)
        layout = QVBoxLayout()
        self.widget = widget
        self.name = name
        layout.addWidget(QLabel(self.name))
        layout.addWidget(self.widget)
        self.collapsed = False
        self.setLayout(layout)

    def toggle(self):
        self.collapsed = not self.collapsed
        if self.collapsed:
            self.hide()
        else:
            self.show()
        self.toggled.emit(self.collapsed)
