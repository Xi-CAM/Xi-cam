from typing import Any, Callable, Iterable, List

from databroker.core import BlueskyRun
from qtpy.QtCore import Qt, QModelIndex, QAbstractItemModel
from qtpy.QtGui import QFont, QBrush, QPalette
from qtpy.QtWidgets import QApplication
from xicam.core.data import ProjectionNotFound
from xicam.core.data.bluesky_utils import display_name
from xicam.core.intents import Intent
from xicam.core.msg import logMessage, WARNING, notifyMessage
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
    active_role = Qt.UserRole + 4  # only tied to Ensemble tree items

    # Unnamed items (i.e. no display role text) will get this text set
    _defaultDisplayText = "Untitled"
    NO_ACTIVE_ENSEMBLE_TEXT = "(None)"

    def __init__(self, parent=None):
        super(EnsembleModel, self).__init__(parent)

        # Keep track of current active item (can be 0 or 1 active items)
        self.active_ensemble = None
        self._active_ensemble_name = self.NO_ACTIVE_ENSEMBLE_TEXT

        # Display the active item as the root title as well
        self.rootItem.setData(f"Active Item: {self.active_ensemble_name}", Qt.DisplayRole)

    def _update_title(self, name):
        # Use default text if there isn't an active ensemble name set yet
        if name is None:
            name = self._defaultDisplayText
        self.rootItem.setData(f"Active Item: {name}", Qt.DisplayRole)
        self.headerDataChanged.emit(Qt.Horizontal, 0, 0)

    @property
    def active_ensemble_name(self):
        if self.active_ensemble is not None:
            self._active_ensemble_name = self.active_ensemble.data(Qt.DisplayRole)
        else:
            self._active_ensemble_name = self.NO_ACTIVE_ENSEMBLE_TEXT
        return self._active_ensemble_name

    def index_from_catalog(self, catalog: BlueskyRun):
        root_index = self.index(self.active_ensemble.row(), 0)
        index = self.match(self.index(0, 0, root_index), self.object_role, catalog, hits=1)[0]
        return index

    def catalogs_from_ensemble(self, ensemble: TreeItem):
        return ensemble.data(self.object_role).catalogs

    def intents_from_catalog(self, catalog: BlueskyRun):
        # find the item containing this catalog
        catalog_index = self.index_from_catalog(catalog)
        catalog_item = self.getItem(catalog_index)

        # get all children (intents) of this catalog
        children = [catalog_item.child(i).data(self.object_role) for i in range(catalog_item.childCount())]
        return children

    def intents_from_ensemble(self, ensemble: TreeItem):
        return {catalog: self.intents_from_catalog(catalog) for catalog in self.catalogs_from_ensemble(ensemble)}


    def _set_active_brushes(self, index, is_active):
        brush = text_brush = self.data(index, Qt.BackgroundRole) or QBrush()
        font = self.data(index, Qt.FontRole) or QFont()
        if is_active is True:
            if self.active_ensemble is not None:
                # self.active_ensemble.setData(False, self.active_role)
                active_index = self.index(self.active_ensemble.row(), 0)
                self.setData(active_index, False, self.active_role)
            self.active_ensemble = self.getItem(index)
            self._update_title(self.active_ensemble_name)
            palette = QApplication.palette()
            brush = palette.color(QPalette.Normal, QPalette.Highlight)
            text_brush = palette.color(QPalette.Normal, QPalette.BrightText)
            font.setBold(True)
        else:
            self.active_ensemble = None
            brush = QBrush()
            text_brush = QBrush()
            font.setBold(False)
        self.setData(index, brush, Qt.BackgroundRole)
        self.setData(index, text_brush, Qt.ForegroundRole)
        self.setData(index, font, Qt.FontRole)

    def setData(self, index: QModelIndex, value: Any, role: Qt.ItemDataRole = Qt.EditRole) -> bool:
        if not index.isValid():
            return False

        if role == self.active_role:
            self._set_active_brushes(index, value)

        elif role == Qt.DisplayRole:
            # Intercept display text changes for ensembles (i.e. renaming) so we can update the title
            # also ONLY update the title if it is the active item
            if index.data(self.data_type_role) == WorkspaceDataType.Ensemble and index.data(self.active_role):
                self._update_title(value)

        # Add other role handling here
        else:
            ...

        return super(EnsembleModel, self).setData(index, value, role)

    def _create_catalog_item(self, ensemble_item, catalog, projectors: List[Callable[[BlueskyRun], List[Intent]]]):
        catalog_item = TreeItem(ensemble_item)
        catalog_name = display_name(catalog)
        catalog_item.setData(catalog_name, Qt.DisplayRole)
        catalog_item.setData(catalog, self.object_role)
        catalog_item.setData(WorkspaceDataType.Catalog, self.data_type_role)
        # We want to notify the user if all projections failed
        _any_projection_succeeded = False
        for projector in projectors:
            try:
                intents = projector(catalog)
                for intent in intents:
                    self._create_intent_item(catalog_item, intent)
            except (AttributeError, ProjectionNotFound) as e:
                logMessage(e, level=WARNING)
            else:
                _any_projection_succeeded = True
                ensemble_item.appendChild(catalog_item)

        if not _any_projection_succeeded:
            notifyMessage("Data file was opened, but could not be interpreted in this GUI plugin.")

    def _create_intent_item(self, catalog_item, intent):
            intent_item = TreeItem(catalog_item)
            intent_item.setData(intent.item_name, Qt.DisplayRole)
            intent_item.setData(intent, self.object_role)
            intent_item.setData(WorkspaceDataType.Intent, self.data_type_role)
            catalog_item.appendChild(intent_item)

    def append_to_ensemble(self, catalog, ensemble, projectors: List[Callable[[BlueskyRun], List[Intent]]]):
        # Find the active ensemble (may be none if ensemble model is empty)
        ensemble_item = self.active_ensemble
        if ensemble_item is not None:
            end_row = ensemble_item.childCount()
            # Use begin/end to notify views (e.g. dataselectorview) that it needs to update view after item is inserted
            self.beginInsertRows(self.index(ensemble_item.row(), 0), end_row, end_row+1)
            self._create_catalog_item(ensemble_item, catalog, projectors)
            self.endInsertRows()
        else:
            self.add_ensemble(ensemble, projectors)

    def add_ensemble(self, ensemble: Ensemble, projectors: List[Callable[[BlueskyRun], List[Intent]]]):
        """Add an ensemble to the model.

        Requires a projector, which is a function that accepts a BluesyRun catalog
        and returns a list of Intents.
        """
        # self.layoutAboutToBeChanged.emit()
        ensemble_item = TreeItem(self.rootItem)
        ensemble_item.setFlags(ensemble_item.flags() | Qt.ItemIsEditable)
        # Note we do NOT provide display text; then TreeModel handles the naming for us
        ensemble_item.setData(ensemble, self.object_role)
        ensemble_item.setData(WorkspaceDataType.Ensemble, self.data_type_role)

        for catalog in ensemble.catalogs:
            self._create_catalog_item(ensemble_item, catalog, projectors)

        self.rootItem.appendChild(ensemble_item)
        # First ensemble should be activated; others not
        if self.rowCount() == 1:
            self.setData(self.index(ensemble_item.row(), 0), True, self.active_role)
        self.layoutChanged.emit()  # inform any attached views that they need to update

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

    def data(self, index: QModelIndex, role=Qt.DisplayRole) -> Any:
        item = self.getItem(index)

        if role == self.active_role:
            if item == self.active_ensemble:
                return True
            return False

        # Handle case where display text not provided
        elif role == Qt.DisplayRole:
            data = item.data(role)
            font = self.data(index, Qt.FontRole) or QFont()
            if data is None or data == self._defaultDisplayText:
                item.setData(self._defaultDisplayText, role)
                font.setItalic(True)
            item.setData(font, Qt.FontRole)
            return item.data(role)

        else:
            return super(EnsembleModel, self).data(index, role)


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
        if not index.isValid():
            return None

        elif role == Qt.DisplayRole:
            intent = index.internalPointer()
            return intent.item_name

        elif role == EnsembleModel.object_role:
            return index.internalPointer()

        return None
