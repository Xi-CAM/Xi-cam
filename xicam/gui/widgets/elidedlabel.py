from qtpy.QtCore import Qt
from qtpy.QtGui import QFontMetrics, QPainter
from qtpy.QtWidgets import QApplication, QLabel


class ElidedLabel(QLabel):
    def setText(self, text):
        self._text = text
        metrics = QFontMetrics(self.font())
        elided = metrics.elidedText(self._text, Qt.ElideRight, self.width())
        super(ElidedLabel, self).setText(elided)
