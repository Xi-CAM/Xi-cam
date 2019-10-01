from qtpy.QtCore import QSize, Qt
from qtpy.QtGui import QPixmap, QIcon
from qtpy.QtWidgets import QLineEdit, QToolButton, QStyle

from xicam.gui.static import path


class SearchLineEdit(QLineEdit):
    def __init__(self, text="", clearable=True, parent=None):
        QLineEdit.__init__(self, text=text, parent=parent)

        searchPixmap = QPixmap(str(path("icons/search.png")))

        clearPixmap = QPixmap(str(path("icons/clear.png")))
        self.clearButton = QToolButton(self)
        self.clearButton.setIcon(QIcon(clearPixmap))
        self.clearButton.setIconSize(QSize(16, 16))
        self.clearButton.setCursor(Qt.ArrowCursor)
        self.clearButton.setStyleSheet("QToolButton { border: none; padding: 0 px;}")
        self.clearButton.hide()

        if clearable:
            self.clearButton.clicked.connect(self.clear)
            self.textChanged.connect(self.updateCloseButton)

        self.searchButton = QToolButton(self)
        self.searchButton.setIcon(QIcon(searchPixmap))
        self.searchButton.setIconSize(QSize(16, 16))
        self.searchButton.setStyleSheet("QToolButton { border: none; padding: 0 px;}")

        frameWidth = self.style().pixelMetric(QStyle.PM_DefaultFrameWidth)
        self.setStyleSheet(
            "QLineEdit { padding-left: %spx; padding - right: % spx;} "
            % (self.searchButton.sizeHint().width() + frameWidth + 1, self.clearButton.sizeHint().width() + frameWidth + 1)
        )
        msz = self.minimumSizeHint()
        self.setMinimumSize(
            max(msz.width(), self.searchButton.sizeHint().width() + self.clearButton.sizeHint().width() + frameWidth * 2 + 2),
            max(msz.height(), self.clearButton.sizeHint().height() + frameWidth * 2 + 2),
        )

    #        self.searchMenu = QtGui.QMenu(self.searchButton)
    #        self.searchButton.setMenu(self.searchMenu)
    #        self.searchMenu.addAction("Google")
    #        self.searchButton.setPopupMode(QtGui.QToolButton.InstantPopup)

    def resizeEvent(self, event):
        sz = self.clearButton.sizeHint()
        frameWidth = self.style().pixelMetric(QStyle.PM_DefaultFrameWidth)
        self.clearButton.move(self.rect().right() - frameWidth - sz.width(), (self.rect().bottom() + 1 - sz.height()) / 2)
        self.searchButton.move(self.rect().left() + 1, (self.rect().bottom() + 1 - sz.height()) / 2)

    def updateCloseButton(self, text):
        if text:
            self.clearButton.setVisible(True)
        else:
            self.clearButton.setVisible(False)
