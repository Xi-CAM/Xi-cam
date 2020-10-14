from typing import Any, Callable, Iterable

from PyQt5.QtCore import Qt, QModelIndex, QAbstractItemModel
from xicam.core.data.bluesky_utils import display_name
from xicam.core.msg import logMessage, WARNING
from xicam.core.workspace import WorkspaceDataType, Ensemble
from xicam.gui.models.treemodel import TreeModel, TreeItem


class EnsembleModel(TreeModel):
    """TreeModel that stores Ensembles.

    Defines custom roles:
    object_role: contains a reference to item's data (this is the custom UserRole commonly used as Qt.UserRole + 1)
    data_type_role: indicates what WorkspaceDataType the item is
    canvas_role: reference to an associated canvas (may not be set if not applicable)

    """
    object_role = Qt.UserRole + 1
    data_type_role = Qt.UserRole + 2
    canvas_role = Qt.UserRole + 3

    def __init__(self, parent=None):
        super(EnsembleModel, self).__init__(parent)
        self.rootItem.setData("Ensembles", Qt.DisplayRole)

    def setData(self, index: QModelIndex, value: Any, role: Qt.ItemDataRole = Qt.EditRole) -> bool:
        if not index.isValid():
            return False
        item = self.getItem(index)
        # if role in (self.object_role, self.canvas_role, self.data_type_role):
            # item.itemData[role] = value
        # if role == Qt.CheckStateRole:
        #     success = super(EnsembleModel, self).setData(index, True, self.state_changed_role)
        #     if not success:
        #         return False
        return super(EnsembleModel, self).setData(index, value, role)

    def add_ensemble(self, ensemble: Ensemble, projector: Callable):
        ensemble_item = TreeItem(self.rootItem)
        # ensemble_item = ensemble
        ensemble_item.setData(ensemble.name, Qt.DisplayRole)
        ensemble_item.setData(ensemble, self.object_role)
        ensemble_item.setData(WorkspaceDataType.Ensemble, self.data_type_role)

        for catalog in ensemble.catalogs:
            catalog_item = TreeItem(ensemble_item)
            catalog_name = display_name(catalog)
            catalog_item.setData(catalog_name, Qt.DisplayRole)
            catalog_item.setData(catalog, self.object_role)
            catalog_item.setData(WorkspaceDataType.Catalog, self.data_type_role)

            try:
                intents = projector(catalog)
                for intent in intents:
                    intent_item = TreeItem(catalog_item)
                    intent_item.setData(intent.item_name, Qt.DisplayRole)
                    intent_item.setData(intent, self.object_role)
                    intent_item.setData(WorkspaceDataType.Intent, self.data_type_role)
                    catalog_item.appendChild(intent_item)
            except AttributeError as e:
                logMessage(e, level=WARNING)

            ensemble_item.appendChild(catalog_item)

        self.rootItem.appendChild(ensemble_item)
        self.layoutChanged.emit()

    def remove_ensemble(self, ensemble):
        # TODO
        raise NotImplementedError

    def rename_ensemble(self, ensemble, name):
        # TODO, defer to setData w/ EditRole
        found_ensemble_items = self.findItems(ensemble.name)
        if found_ensemble_items:
            ensemble_item = found_ensemble_items[0]
            # Better way to do this (CatalogItem.setData can auto rename)
            ensemble = ensemble_item.data(Qt.UserRole)
            ensemble.name = name
            ensemble_item.setData(name, Qt.DisplayRole)


class IntentsModel(QAbstractItemModel):
    def __init__(self):
        super(IntentsModel, self).__init__()

        self._source_model: QAbstractItemModel = None
        self._source_indexes = []

    def _intent_source_indexes_gen(self):
        for ensemble_row in range(self._source_model.rowCount(QModelIndex())):
            ensemble_index = self._source_model.index(ensemble_row, 0)
            for run_row in range(self._source_model.rowCount(ensemble_index)):
                run_index = self._source_model.index(run_row, 0, ensemble_index)
                for intent_row in range(self._source_model.rowCount(run_index)):
                    intent_index = self._source_model.index(intent_row, 0, run_index)
                    if intent_index.data(Qt.CheckStateRole) != Qt.Unchecked:
                        yield intent_index

    @property
    def _intent_source_indexes(self):
        if not self._source_indexes:
            self._source_indexes = list(self._intent_source_indexes_gen())
        return self._source_indexes

    def setSourceModel(self, model):
        self._source_model = model
        self._source_model.dataChanged.connect(self.sourceDataChanged)

    def sourceDataChanged(self, topLeft: QModelIndex, bottomRight: QModelIndex, roles: Iterable[int] = ...) -> None:
        # Invalidate cache
        self._source_indexes.clear()

        # TODO: translate source model indexes into intentsmodel indexes and emit those rather than emit all
        self.dataChanged.emit(self.index(0, 0), self.index(self.rowCount()-1, 0), roles)

    def sourceModel(self):
        return self._source_model

    def index(self, row, column, parent=QModelIndex()):
        try:
            intent_index = self._intent_source_indexes[row]  # FIXME: THIS IS KINDA INEFFICIENT
            i = self.createIndex(row, column, intent_index)
            return i

        # FIXME: target specific exception or handle differently
        except Exception:
            return QModelIndex()

    def parent(self, child):
        return QModelIndex()

    def rowCount(self, parent=QModelIndex()):
        if not parent.isValid():
            return len(self._intent_source_indexes)
        else:
            return 0

    def columnCount(self, parent):
        if not parent.isValid():
            return 1
        else:
            return 0

    def data(self, index, role=Qt.DisplayRole):
        # print(f"IntentsModel.data({index.data()}, {role} -> {self._source_model.data(index, role)}")

        if not index.isValid():
            return None

        elif role == Qt.DisplayRole:
            intent = index.internalPointer()
            return intent.item_name

        elif role == EnsembleModel.object_role:
            return index.internalPointer()

        return None