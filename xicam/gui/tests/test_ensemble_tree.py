import pytest
from qtpy.QtCore import Qt, QModelIndex, QAbstractItemModel
from qtpy.QtGui import QPainter, QStandardItemModel, QStandardItem
from qtpy.QtWidgets import QApplication, QHBoxLayout, QWidget, \
    QPushButton, QSpinBox, QVBoxLayout, QStyleOptionViewItem, QStyledItemDelegate, QLineEdit
from xicam.core.workspace import Ensemble
from xicam.gui.models.treemodel import IntentsModel, EnsembleModel
from xicam.gui.views.tabview import IntentsTabView
from xicam.gui.views.treeview import DataSelectorView
from pytestqt import qtbot


class AddRemoveItemsDemoWidget(QWidget):
    def __init__(self, model=None, parent=None):
        super(AddRemoveItemsDemoWidget, self).__init__(parent)
        self.model = model
        if self.model is None:
            self.model = QStandardItemModel()
        self.index_box = QSpinBox()
        self.index_box.setValue(0)
        self.index_box.setMinimum(0)
        self.index_box.setMaximum(0)

        self.add_button = QPushButton("Add Item")
        self.add_button.clicked.connect(self.prepare_add_item)
        self.remove_button = QPushButton("Remove Item")
        self.remove_button.clicked.connect(self.prepare_remove_item)

        inner_layout = QVBoxLayout()
        inner_layout.addWidget(self.add_button)
        inner_layout.addWidget(self.remove_button)
        inner_layout.addWidget(self.index_box)
        self.setLayout(inner_layout)

    def prepare_add_item(self, _):
        self.add_item(self.index_box.value())

    def add_item(self, i):
        item = QStandardItem(f'item {self.model.rowCount()}')
        self.model.insertRow(i, item)
        self.index_box.setMaximum(self.model.rowCount())

    def prepare_remove_item(self, _):
        self.remove_item(self.index_box.value())

    def remove_item(self, i):
        self.model.removeRow(i)
        self.index_box.setMaximum(self.model.rowCount())


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


@pytest.mark.skip(reason="need test data that can generate catalogs and intents")
def test_ensemble_tree(qtbot):
    from xicam.plugins import manager as plugin_manager

    plugin_manager.qt_is_safe = True
    plugin_manager.initialize_types()
    plugin_manager.collect_plugins()

    # Create Ensemble
    ensemble1 = Ensemble()

    # Add runs to the ensemble
    import databroker

    db_catalog = databroker.catalog['local']
    run1 = db_catalog['02e23b31']  # TODO: replace this with generating catalogs from data files
    run2 = db_catalog['b6dd84']
    ensemble1.append_catalog(run1)
    ensemble1.append_catalog(run2)

    # Import projectors
    from xicam.SAXS.projectors.nxcansas import project_nxcanSAS
    from xicam.SAXS.projectors.edf import project_NXsas

    # Bind ensemble and projectors to ensemble model
    ensemble_model = EnsembleModel()
    ensemble_model.appendEnsemble(ensemble1, [project_NXsas, project_nxcanSAS])

    # Bind to views
    # view = QTreeView()
    view = DataSelectorView()
    view.setModel(ensemble_model)
    tab_view = IntentsTabView()
    intents_model = IntentsModel(ensemble_model)
    tab_view.setModel(intents_model)

    def check_index(index):
        obj = index.internalPointer()
        return obj

    view.clicked.connect(check_index)
    view.setHeaderHidden(True)
    view.expandAll()

    layout = QHBoxLayout()
    layout.addWidget(tab_view)
    layout.addWidget(view)
    # layout.addWidget(w)

    widget = QWidget()
    widget.setLayout(layout)
    widget.show()

    qtbot.waitForWindowShown(widget)
