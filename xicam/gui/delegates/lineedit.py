from qtpy.QtCore import QModelIndex, Qt, QAbstractItemModel
from qtpy.QtGui import QPainter
from qtpy.QtWidgets import QStyledItemDelegate, QStyleOptionViewItem, QWidget, QLineEdit


class LineEditDelegate(QStyledItemDelegate):
    """Custom editing delegate that allows renaming text and updating placeholder text in a line edit.

    This class was written for using with the DataSelectorView.
    """
    def __init__(self, parent=None):
        super(LineEditDelegate, self).__init__(parent)
        self._default_text = "Untitled"

    def createEditor(self, parent: QWidget,
                     option: QStyleOptionViewItem,
                     index: QModelIndex) -> QWidget:
        editor = QLineEdit(parent)
        editor.setPlaceholderText(self._default_text)
        editor.setFrame(False)
        return editor

    def setEditorData(self, editor: QWidget, index: QModelIndex):
        value = index.model().data(index, Qt.DisplayRole)
        editor.setText(value)

    def setModelData(self, editor: QWidget,
                     model: QAbstractItemModel,
                     index: QModelIndex):

        text = editor.text()
        if text == "":
            text = editor.placeholderText()
        # Update the "default" text to the previous value edited in
        self._default_text = text
        model.setData(index, text, Qt.DisplayRole)

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex):
        super(LineEditDelegate, self).paint(painter, option, index)
        return

        # if index.data(role=EnsembleModel.active_role):
        #     active_brush = QBrush(Qt.cyan)
        #     painter.save()
        #     painter.fillRect(option.rect, active_brush)
        #     painter.restore()
        #
        # super(LineEditDelegate, self).paint(painter, option, index)