import sys
from qtpy.QtWidgets import QLineEdit, QListWidget, QFormLayout, QHBoxLayout, QRadioButton,\
                           QWidget, QStackedWidget, QCheckBox, QToolButton, QStyle, QLabel, QGraphicsView, QApplication

from xicam.gui.widgets.views import StackedCanvasView


if __name__ ==  "__main__":
    app = QApplication(sys.argv)
    ex = StackedCanvasView()
    sys.exit(app.exec_())

