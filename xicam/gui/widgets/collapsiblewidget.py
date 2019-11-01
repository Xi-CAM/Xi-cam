from qtpy.QtCore import Qt, Signal
from qtpy.QtWidgets import QLabel, QGridLayout, QSplitter, QToolBar, QVBoxLayout, QWidget

from xicam.core.msg import logError


class CollapsibleWidget(QWidget):

    toggled = Signal(bool)

    def __init__(self, widget: QWidget, buttonText: str, parent=None):
        super(CollapsibleWidget, self).__init__(parent)
        self.widget = widget
        self.buttonText = buttonText
        self.collapsed = False

        toolBar = QToolBar()
        action = toolBar.addAction(self.name, self.toggle)
        action.setIconText("&" + action.text())
        self.collapseButton = toolBar.widgetForAction(action)
        self.collapseButton.setCheckable(True)
        self.collapseButton.setChecked(not self.collapsed)

        self.splitter = QSplitter(Qt.Horizontal)
        self.splitter.addWidget(self.widget)
        self.splitter.setCollapsible(0, self.collapsed)

        layout = QGridLayout()
        layout.addWidget(self.splitter, 0, 0)
        layout.addWidget(toolBar, 1, 0)

        self.setLayout(layout)

        self.toggled.connect(self.collapse)

    def addWidget(self, widget):
        self.splitter.addWidget(widget)
        self.splitter.setCollapsible(1, False)

    def toggle(self):
        self.collapsed = not self.collapsed
        self.toggled.emit(self.collapsed)

    def collapse(self, collapsed):
        self.collapseButton.setChecked(not collapsed)
        self.splitter.setCollapsible(0, collapsed)
        try:
            if collapsed:
                sizes = []
                for i in range(self.splitter.count()):
                    sizes.append(self.splitter.widget(i).minimumSizeHint().width())
                sizes[0] = 0
                self.splitter.setSizes(sizes)
            else:
                sizes = []
                for i in range(self.splitter.count()):
                    sizes.append(self.splitter.sizes()[i])
                sizes[0] = self.splitter.widget(i).minimumSizeHint().width()
                self.splitter.setSizes(sizes)
        except Exception as e:
            logError(e)
