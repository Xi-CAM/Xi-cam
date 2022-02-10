from databroker.core import BlueskyRun
from qtpy.QtCore import Qt, QModelIndex, QPoint, QRect
from qtpy.QtGui import QStandardItemModel, QStandardItem
from qtpy.QtWidgets import QApplication, QHBoxLayout, QLabel, QListView, QWidget, \
    QPushButton, QSpinBox, QVBoxLayout, QTabWidget, QAbstractItemView, QTreeView
from xicam.core.data import ProjectionNotFound
from xicam.core.intents import Intent
from xicam.core.msg import notifyMessage, logMessage, WARNING
from xicam.gui.models.treemodel import IntentsModel, TreeModel
from xicam.core.workspace import Ensemble
from xicam.gui.views.tabview import TabView, IntentsTabView


# import databroker.tutorial_utils
#
# # Catalog of many small Runs
# databroker.tutorial_utils.fetch_BMM_example()
# catalog = databroker.catalog['bluesky-tutorial-BMM']
# run = catalog[-1]



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


class EnsembleModel(TreeModel):

    def appendIntent(self, intent: Intent, catalog):
        # return True  # should show "Ensemble 1" with child <uid> in view

        intent_parent = catalog
        intent_count = self.tree.child_count(catalog)
        intent_parent_index = self.createIndex(intent_count, 0, intent_parent)
        self.beginInsertRows(intent_parent_index, intent_count, intent_count + 1)
        self.tree.add_node(intent, catalog)
        self.endInsertRows()

        # self.tree.add_node(intent, catalog)
        #
        # intent_row, intent_parent = self.tree.index(intent)
        # parent_index = self.createIndex(intent_row, 0, intent_parent)
        # self.beginInsertRows(parent_index, intent_row, intent_row + 1)
        # self.endInsertRows()

    def appendCatalog(self, ensemble: Ensemble, catalog: BlueskyRun, projectors):
        catalog_parent = ensemble
        catalog_count = self.tree.child_count(ensemble)
        catalog_parent_index = self.createIndex(catalog_count, 0, catalog_parent)
        self.beginInsertRows(catalog_parent_index, catalog_count, catalog_count + 1)
        self.tree.add_node(catalog, parent=ensemble)
        self.endInsertRows()

        # # return True  # should show only "Ensemble 1" in view
        # self.tree.add_node(catalog, parent=ensemble)
        # catalog_row, catalog_parent = self.tree.index(catalog)
        # parent_index = self.createIndex(catalog_row, 0, catalog_parent)  # type: QModelIndex
        # parent_obj = parent_index.internalPointer()
        #
        # self.beginInsertRows(parent_index, catalog_row, catalog_row + 1)
        # self.endInsertRows()

        _any_projection_succeeded = False
        for projector in projectors:
            try:
                intents = projector(catalog)
            except (AttributeError, ProjectionNotFound) as e:
                logMessage(e, level=WARNING)
            else:
                _any_projection_succeeded = True
                for intent in intents:
                    self.appendIntent(intent, catalog)

        if not _any_projection_succeeded:
            notifyMessage("Data file was opened, but could not be interpreted in this GUI plugin.")

    def appendEnsemble(self, ensemble: Ensemble, projectors):
        parent_node = None
        parent_index = QModelIndex()
        ensemble_count = self.rowCount(parent_index)
        self.beginInsertRows(parent_index, ensemble_count, ensemble_count + 1)
        self.tree.add_node(ensemble, parent_node)
        self.endInsertRows()
        # return

        for catalog in ensemble.catalogs:
            self.appendCatalog(ensemble, catalog, projectors)


        # self.tree.add_node(ensemble)
        # ensemble_row, ensemble_parent = self.tree.index(ensemble)
        # parent_index = self.createIndex(ensemble_row, 0, ensemble_parent)
        # self.beginInsertRows(parent_index, ensemble_row, ensemble_row + 1)
        #
        # for catalog in ensemble.catalogs:
        #     self.appendCatalog(ensemble, catalog, projectors)
        # self.endInsertRows()
        #
        # ensemble_index = self.index(self.rowCount(parent_index) - 1, 0, parent_index)
        # catalog_index = self.index(self.rowCount(ensemble_index) - 1, 0, ensemble_index)
        # ensemble_obj = ensemble_index.internalPointer()
        # catalog_obj = catalog_index.internalPointer()
        # ensemble_text = self.data(ensemble_index)
        # catalog_text = self.data(catalog_index)
        # print()


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
        # tab_view.setModel(intents_model)

    else:
        w = AddRemoveItemsDemoWidget()
        view = QListView()
        view.setModel(w.model)
        tab_view = TabView()
        tab_view.setModel(w.model)


    layout = QHBoxLayout()
    layout.addWidget(tab_view)
    layout.addWidget(view)
    # layout.addWidget(w)

    widget = QWidget()
    widget.setLayout(layout)
    widget.show()

    app.exec_()