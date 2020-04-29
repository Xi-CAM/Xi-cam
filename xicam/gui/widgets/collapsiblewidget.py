from qtpy.QtCore import Qt, Signal
from qtpy.QtWidgets import QGridLayout, QSplitter, QToolBar, QWidget


# TODO: this could be more generic, defining a collapsible interface/mixin type class
class CollapsibleWidget(QWidget):
    """
    Creates a widget that can be collapsed when a button is clicked.
    """

    toggled = Signal(bool)

    def __init__(self, widget: QWidget, buttonText: str, parent=None):
        """
        Constructs a widget that lets the passed ``widget`` keep an internal collapsed state that can be triggered when
        a button is clicked.

        Internally, when the button is clicked, a toggled signal is emitted, indicating what the collapse state has
        been toggled to. Additionally, this signal is connected to the collapse() slot, which will collapse the passed
        widget if another widget has been added via addWidget(). The widget added via addWidget() is not collapsible.

        Parameters
        ----------
        widget
            The widget to make collapsible.
        buttonText
            The text of the button that will be used to collapse.
        parent
            The parent widget.
        """
        super(CollapsibleWidget, self).__init__(parent)
        self.widget = widget
        self.buttonText = buttonText
        self.collapsed = False

        toolBar = QToolBar()
        action = toolBar.addAction(self.buttonText, self.toggle)
        action.setIconText("&" + action.text())
        self.collapseButton = toolBar.widgetForAction(action)
        self.collapseButton.setCheckable(True)
        self.collapseButton.setChecked(not self.collapsed)

        self.splitter = QSplitter(Qt.Horizontal)
        self.splitter.addWidget(self.widget)
        self.splitter.setCollapsible(0, self.collapsed)
        # Keep track of the collapsed widget's size to restore properly when un-collapsed
        self.widgetSize = self.splitter.sizes()[0]

        layout = QGridLayout()
        layout.addWidget(self.splitter, 0, 0)
        layout.addWidget(toolBar, 1, 0)

        self.setLayout(layout)

        self.toggled.connect(self.collapse)

    def addWidget(self, widget):
        """
        Adds a non-collapsible widget to the internal splitter.

        Parameters
        ----------
        widget
            Non-collapsible widget to add.
        """
        # TODO -- what happens when more than one widget is added?
        self.splitter.addWidget(widget)
        self.splitter.setCollapsible(1, False)

    def toggle(self):
        self.collapsed = not self.collapsed
        self.toggled.emit(self.collapsed)

    def collapse(self, collapsed):
        self.collapseButton.setChecked(not collapsed)
        self.splitter.setCollapsible(0, collapsed)
        # Only do something for now if there is more than one widget added.
        if len(self.splitter.sizes()) > 1:
            if collapsed:
                self.widgetSize = self.splitter.sizes()[0]
                sizes = [0, self.splitter.sizes()[1]]
                self.splitter.setSizes(sizes)
            else:
                sizes = [self.widgetSize, self.splitter.sizes()[1] - self.widgetSize]
                self.splitter.setSizes(sizes)
