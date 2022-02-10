from databroker.core import BlueskyRun
from qtpy.QtCore import Qt, QModelIndex, QPoint, QRect
from qtpy.QtGui import QStandardItemModel, QStandardItem
from qtpy.QtWidgets import QApplication, QHBoxLayout, QLabel, QListView, QWidget, \
    QPushButton, QSpinBox, QVBoxLayout, QTabWidget, QAbstractItemView, QTreeView
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
        view = QTreeView()
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