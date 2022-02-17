from databroker.core import BlueskyRun
from qtpy.QtCore import Qt, QModelIndex, QPoint, QRect, QAbstractItemModel
from qtpy.QtGui import QPainter, QStandardItemModel, QStandardItem
from qtpy.QtWidgets import QApplication, QHBoxLayout, QLabel, QListView, QWidget, \
    QPushButton, QSpinBox, QVBoxLayout, QTabWidget, QAbstractItemView, QTreeView, \
    QStyleOptionViewItem, QStyledItemDelegate, QLineEdit, QMenu, QAction
from xicam.core.data import ProjectionNotFound
from xicam.core.intents import Intent
from xicam.core.msg import notifyMessage, logMessage, WARNING
from xicam.gui.models.treemodel import IntentsModel, TreeModel, EnsembleModel
from xicam.core.workspace import Ensemble
from xicam.gui.views.tabview import TabView, IntentsTabView


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


class DataSelectorView(QTreeView):
    def __init__(self, parent=None):
        super(DataSelectorView, self).__init__(parent)

        # We are implementing our own custom context menu
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.customMenuRequested)

        # Don't allow double-clicking for expanding; use it for editing
        self.setExpandsOnDoubleClick(False)
        self.setEditTriggers(QAbstractItemView.DoubleClicked)

        # Attach a custom delegate for the editing
        delegate = LineEditDelegate(self)
        self.setItemDelegate(delegate)

        self.setDragEnabled(True)

        self.setAnimated(True)

        self.setWhatsThis("This widget helps organize and display any loaded data or data created within Xi-CAM. "
                          "Data is displayed in a tree-like manner:\n"
                          "  Collection\n"
                          "    Catalog\n"
                          "      Visualizable Data\n"
                          "Click on the items' checkboxes to visualize them.\n"
                          "Right-click a Collection to rename it.\n"
                          "Right-click in empty space to create a new Collection.\n")

    def setModel(self, model):
        try:
            self.model().rowsInserted.disconnect(self._expand_rows)
        except Exception:
            ...
        super(DataSelectorView, self).setModel(model)
        self.model().rowsInserted.connect(self._expand_rows)

    def _expand_rows(self, parent: QModelIndex, first: int, last: int):
        self.expandRecursively(parent)

    def _rename_action(self, _):
        # Request editor (see the delegate created in the constructor) to change the ensemble's name
        self.edit(self.currentIndex())

    def _remove_action(self, _):
        index = self.currentIndex()  # QModelIndex
        removed = self.model().removeRow(index.row(), index.parent())
        # self.model().dataChanged.emit(QModelIndex(), QModelIndex())
        ...

    def _create_ensemble_action(self, _):
        ensemble = Ensemble()
        # Note this ensemble has no catalogs; so we don't need projectors passed (just [])
        self.model().appendEnsemble(ensemble, [], active=True)

    def _set_active_action(self, _):
        # Update the model data with the currentIndex corresponding to where the user right-clicked
        # Update the active role based on the value of checked
        # self.model().setData(self.currentIndex(), checked, EnsembleModel.active_role)
        self.model().activeEnsemble = self.currentIndex().internalPointer()

    def customMenuRequested(self, position):
        """Builds a custom menu for items items"""
        index = self.indexAt(position)  # type: QModelIndex
        menu = QMenu(self)

        if index.isValid():

            data = index.internalPointer()
            if isinstance(data, Ensemble):

                # Allow renaming the ensemble via the context menu
                rename_action = QAction("Rename Collection", menu)
                rename_action.triggered.connect(self._rename_action)
                menu.addAction(rename_action)

                # Allow toggling the active ensemble via the context menu
                # * there can only be at most 1 active ensemble
                # * there are only 0 active ensembles when data has not yet been loaded ???
                # * opening data updates the active ensemble to that data
                is_active = bool(self.model().activeEnsemble == data)
                active_text = "Active"
                set_active_action = QAction(active_text, menu)
                if is_active is True:
                    set_active_action.setEnabled(False)
                else:
                    set_active_action.setEnabled(True)
                    set_active_action.setText(f"Set {active_text}")

                # Make sure to update the model with the active / deactivated ensemble
                set_active_action.triggered.connect(self._set_active_action)
                # Don't allow deactivating the active ensemble if there is only one loaded
                if self.model().rowCount() == 1:
                    set_active_action.setEnabled(False)
                menu.addAction(set_active_action)

                menu.addSeparator()

            remove_text = "Remove "
            if isinstance(data, Ensemble):
                remove_text += "Ensemble"
            elif isinstance(data, BlueskyRun):
                remove_text += "Catalog"
            elif isinstance(data, Intent):
                remove_text += "Item"
            remove_action = QAction(remove_text, menu)
            remove_action.triggered.connect(self._remove_action)
            menu.addAction(remove_action)

        else:
            create_ensemble_action = QAction("Create New Collection", menu)
            create_ensemble_action.triggered.connect(self._create_ensemble_action)
            menu.addAction(create_ensemble_action)

        # Display menu wherever the user right-clicked
        menu.popup(self.viewport().mapToGlobal(position))

if __name__ == "__main__":

    from xicam.plugins import manager as plugin_manager
    app = QApplication([])
    plugin_manager.qt_is_safe = True
    plugin_manager.initialize_types()
    plugin_manager.collect_plugins()

    if True:
        # Create Ensemble
        ensemble1 = Ensemble()

        # Add runs to the ensemble
        import databroker

        db_catalog = databroker.catalog['local']
        run1 = db_catalog['02e23b31']
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

        selected_view = QListView()
        selected_view_model = QStandardItemModel()
        selected_view.setModel(selected_view_model)

        def selection_changed(selection, command):
            selected_view_model.clear()
            for index in selection.indexes():
                item = QStandardItem(index.internalPointer().name)
                selected_view_model.appendRow(item)

        ensemble_model.intent_selection_model.selectionChanged.connect(selection_changed)

    else:
        w = AddRemoveItemsDemoWidget()
        view = QListView()
        view.setModel(w.model)
        tab_view = TabView()
        tab_view.setModel(w.model)


    layout = QHBoxLayout()
    layout.addWidget(tab_view)
    layout.addWidget(view)
    layout.addWidget(selected_view)
    # layout.addWidget(w)

    widget = QWidget()
    widget.setLayout(layout)
    widget.show()

    app.exec_()