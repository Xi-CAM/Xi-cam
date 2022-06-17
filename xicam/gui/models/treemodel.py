import itertools
from collections import defaultdict
from typing import Any, List, Tuple, Union, Iterable
from weakref import WeakValueDictionary

from qtpy.QtGui import QPalette, QBrush
from databroker.core import BlueskyRun
from qtpy.QtCore import Qt, QAbstractItemModel, QModelIndex, QItemSelectionModel, Signal
from qtpy.QtWidgets import QApplication
from xicam.core.data import ProjectionNotFound
from xicam.core.intents import Intent
from xicam.core.msg import logMessage, WARNING, notifyMessage
from xicam.core.threads import invoke_in_main_thread
from xicam.core.workspace import Ensemble
from xicam.plugins import manager as plugin_manager


class Tree:
    def __init__(self):
        super(Tree, self).__init__()
        self._parent_mapping = dict()
        self._child_mapping = defaultdict(list)

    def add_node(self, node: object, parent=None):
        self.insert_node(node, row=len(self._child_mapping[parent]), parent=parent)

    def insert_node(self, node: object, row: int, parent=None):
        if node in self:
            raise ValueError(f"{node} already exists in tree; cannot add")
        self._parent_mapping[node] = parent
        self._child_mapping[parent].insert(row, node)

    def children(self, node: object) -> List[object]:
        if not (node in self or node is None):
            raise KeyError('node not in tree')
        return self._child_mapping[node]

    def parent(self, node: object) -> object:
        return self._parent_mapping[node]

    def remove_node(self, node: object, drop_children=True):
        children = self.children(node)
        if children and not drop_children:
            raise RuntimeError('Cannot remove node; it has children!')
        for child in children:
            self.remove_node(child)
        self._child_mapping[self.parent(node)].remove(node)
        del self._parent_mapping[node]

    def index(self, node: object) -> Tuple[int, object]:
        parent = self._parent_mapping.get(node, None)
        row = self._child_mapping[parent].index(node)
        return row, parent

    def node(self, row, parent=None) -> object:
        if not (parent in self or parent is None):
            raise KeyError('parent not in tree')
        return self._child_mapping[parent][row]

    def __contains__(self, item):
        return item in self._parent_mapping

    # Non-critical convenience methods
    def child_count(self, node: object) -> int:
        if not (node in self or node is None):
            raise KeyError('node not in tree')
        return len(self._child_mapping[node])

    def has_children(self, node: object) -> bool:
        if not (node in self or node is None):
            raise KeyError('node not in tree')
        return bool(self._child_mapping[node])

    def remove_children(self, node: object, drop_grandchildren=True):
        for node in self.children(node):
            self.remove_node(node, drop_children=drop_grandchildren)


class CheckableTree(Tree):
    def __init__(self):
        self._checked = defaultdict(lambda: Qt.Unchecked)
        super(CheckableTree, self).__init__()

    def checked(self, node: object):
        return self._checked[node]

    def set_checked(self, node: object, value: int) -> Tuple[Tuple[int, object], Tuple[int, object]]:
        lowest_node = self._check_recurse_down(node, value)
        highest_node = self._check_recurse_up(node)
        return self.index(lowest_node), self.index(highest_node)

    def _check_recurse_down(self, node: object, value: int) -> object:
        lowest_node = None
        if self._checked[node] != value:
            self._checked[node] = value
            lowest_node = node
            for child in self.children(node):
                lowest_node = self._check_recurse_down(child, value) or lowest_node
        return lowest_node

    def _check_recurse_up(self, node: object) -> object:
        highest_node = None
        parent = self.parent(node)
        if parent is None:
            return node
        siblings_checked = list(map(self.checked, self.children(parent)))
        if all(siblings_checked):
            new_value = Qt.Checked
        elif any(siblings_checked):
            new_value = Qt.PartiallyChecked
        else:
            new_value = Qt.Unchecked
        if self._checked[parent] != new_value:
            self._checked[parent] = new_value
            highest_node = parent
            return self._check_recurse_up(parent) or highest_node
        else:
            return node

    def remove_node(self, node: object, drop_children=True) -> Tuple[int, object]:
        highest_node = self._check_recurse_up(node)
        index = self.index(highest_node)
        del self._checked[node]
        super(CheckableTree, self).remove_node(node, drop_children)
        return index

    def checked_by_type(self, type_: type, parent=None):
        checked_nodes = []
        for child in self.children(parent):
            if isinstance(child, type_) and self.checked(child) == Qt.Checked:
                checked_nodes.append(child)
            if self.checked(child) != Qt.Unchecked:
                checked_nodes.extend(self.checked_by_type(type_, child))
        return checked_nodes

#  index() , parent() , rowCount() , columnCount() , and data()

# Given datachanged range from source model; includes ensembles/runs
# Need minimal range of local intent indexes


class IntentsModel(QAbstractItemModel):
    canvas_role = Qt.UserRole + 1

    def __init__(self, source_model):
        self.tree = source_model.tree
        self.source_model = source_model
        self._canvas_mapping = WeakValueDictionary()
        self._last_checked_items = []
        self._intents_to_remove = tuple()  # source_data_changed manages this
        super(IntentsModel, self).__init__()

        self.source_model.dataChanged.connect(self.source_model_changed)

    @property
    def intents_to_remove(self):
        # Note that this is only ever non-empty during row removal (e.g. after beginRemoveRows, before beginEndRows)
        return self._intents_to_remove

    def index(self, row: int, column: int, parent: QModelIndex = QModelIndex()) -> QModelIndex:
        if not self.hasIndex(row, column, parent):
            return QModelIndex()

        return self.createIndex(row, column, self.tree.checked_by_type(Intent)[row])

    def parent(self, child: QModelIndex) -> QModelIndex:
        return QModelIndex()

    def rowCount(self, parent: QModelIndex = ...) -> int:
        return len(self.tree.checked_by_type(Intent))

    def columnCount(self, parent: QModelIndex = ...) -> int:
        return 1

    def data(self, index: QModelIndex, role: int = ...) -> Any:
        if not index.isValid():
            return None

        node = index.internalPointer()

        if role == Qt.DisplayRole:
            return node.name
        elif role == self.canvas_role:
            # If intent node not in canvas mapping (doesn't have an associated canvas),
            # either examine canvas mapping for keys (intents) w/ identical match_keys,
            # or, create a new canvas
            canvas = self._find_matching_canvas(node)
            if canvas is None:
                canvas = plugin_manager.get_plugin_by_name(node.canvas, "IntentCanvasPlugin")(canvas_name=node.canvas_name)
            self._canvas_mapping[node] = canvas
            canvas.render(node)
            return self._canvas_mapping[node]

        return None

    def _find_matching_canvas(self, node):
        canvas = self._canvas_mapping.get(node, None)
        if node not in self._canvas_mapping:
            for intent, canvas_ref in self._canvas_mapping.items():
                if node.match_key == intent.match_key:
                    canvas = canvas_ref
                    break
        return canvas

    def source_model_changed(self, topLeft: QModelIndex, bottomRight: QModelIndex, roles: Iterable[int] = ...) -> None:
        if Qt.CheckStateRole in roles:
            new_checked_items = self.tree.checked_by_type(Intent)

            if len(new_checked_items) > len(self._last_checked_items):  # insertion
                diff = set(new_checked_items) - set(self._last_checked_items)
                rows = list(map(new_checked_items.index, diff))
                self.beginInsertRows(QModelIndex(), min(rows), max(rows))
                self.endInsertRows()
            elif len(new_checked_items) < len(self._last_checked_items):  # deletion
                # Temporarily store the intents we should remove, so that when beginRemoveRows is
                # captured in a view's rowsAboutToBeRemoved, the view can access these intents
                self._intents_to_remove = tuple(set(self._last_checked_items) - set(new_checked_items))
                # values passed dont matter since this derived model
                # (we can't access unchecked intents in this model via index())
                rows = list(map(self._last_checked_items.index, self._intents_to_remove))
                self.beginRemoveRows(QModelIndex(), min(rows), max(rows))
                # We removed the intents and we must clear the temporary storage of intents to remove
                self._intents_to_remove = tuple()
                self.endRemoveRows()

            self._last_checked_items = new_checked_items


class TreeModel(QAbstractItemModel):
    """Qt-based tree model.

    For now, single-column support only.

    This tree model is an AbstractItem model that is designed to contain (not QStandardItems).
    Two important caveats regarding this:
    1. We cannot defer to super(...).setData(...) in setData, since the parent implementation always returns False
    2. We must update the generic items' data via a private _setData call, which then emits a dataChanged signal
    """

    sigDerivedItemsRemoved = Signal(list)
    sigDerivedItemsAdded = Signal(list)

    def __init__(self, parent=None):
        super(TreeModel, self).__init__(parent)
        self.tree = CheckableTree()
        self.intent_selection_model = QItemSelectionModel()

    def columnCount(self, index: QModelIndex) -> int:
        """Returns the number of columns in the given index."""
        return 1

    def data(self, index: QModelIndex, role=Qt.DisplayRole) -> Any:
        # TODO: this is probably not necessary; since the checkstate can be set/accessed via the item.itemData dict
        """Returns the data of the index with the associated role.
        """
        if not index.isValid():
            return None

        node = index.internalPointer()  # self.tree.node(index.row(), index.parent())

        if isinstance(node, Ensemble):
            if role == Qt.DisplayRole:
                return node.name
            if role == Qt.CheckStateRole:
                return self.tree.checked(node)
        elif isinstance(node, BlueskyRun):
            if role == Qt.DisplayRole:
                return node.name  # TODO: probably needs to be something else here
            if role == Qt.CheckStateRole:
                return self.tree.checked(node)
        elif isinstance(node, Intent):
            if role == Qt.DisplayRole:
                return node.name
            if role == Qt.CheckStateRole:
                return self.tree.checked(node)

        return None

    def flags(self, index: QModelIndex) -> Qt.ItemFlag:
        """Re-implement to additionally ensure that this model is checkable."""
        if not index.isValid():
            # return Qt.NoItemFlags
            return super(TreeModel, self).flags(index)

        return Qt.ItemIsEditable | Qt.ItemIsUserCheckable | Qt.ItemIsEnabled

        # return super(TreeModel, self).flags(index) #| Qt.ItemIsUserCheckable | Qt.ItemIsEditable
        # return Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsUserCheckable

    def headerData(self, section: int, orientation: Qt.Orientation, role: Qt.ItemDataRole) -> Any:
        """Define a horizontal header that uses the root item's DisplayRole to populate its data."""
        # if orientation == Qt.Horizontal and role == Qt.DisplayRole:
        #     return self.rootItem.data(section)

        return None

    def index(self, row: int, column: int, parent: QModelIndex = QModelIndex()) -> QModelIndex:
        """Re-implement the index method to appropriately handle tree-like models.

        Returns an invalid (default-constructed) index if hasIndex fails,
        or if the parent index passed does not have any children.
        """
        if not self.hasIndex(row, column, parent):
            return QModelIndex()

        if not parent.isValid():
            parent_node = None
        else:
            parent_node = parent.internalPointer()

        try:
            node = self.tree.node(row, parent_node)
        except (IndexError, KeyError):
            node = None

        if node:
            return self.createIndex(row, column, node)
        else:
            return QModelIndex()

    def parent(self, index: QModelIndex) -> QModelIndex:
        """Re-implemented to return an invalid index if the index passed's parent is the root item.

        In other words, an index whose parent is the root item does not have a user/view accessible parent.
        """
        if not index.isValid():
            return QModelIndex()

        child_node = index.internalPointer()
        try:
            parent_node = self.tree.parent(child_node)
        except KeyError:
            parent_node = None

        if parent_node is None:
            return QModelIndex()

        parent_row, parents_parent = self.tree.index(parent_node)

        return self.createIndex(parent_row, 0, parent_node)

    def rowCount(self, index: QModelIndex = QModelIndex()) -> int:
        """If an invalid index is passed, returns the childCount of the root item;
        otherwise, returns the index's childCount.
        """

        # supports only single-column data
        if index.column() > 0:
            return 0

        if not index.isValid():
            parent_node = None
        else:
            parent_node = index.internalPointer()

        return self.tree.child_count(parent_node)

    def setData(self, index: QModelIndex, value: Any, role: Qt.ItemDataRole = Qt.EditRole) -> bool:
        """Re-implemented to set the associated item's itemData property and emit dataChanged.

        Special case for CheckStateRole handles checking of all children (recursively)
        and all ancestors to appropriate check states (including PartiallyChecked states).

        Returns True if the data was successfully set.
        """
        if not index.isValid():
            return False

        node = index.internalPointer()

        if role == Qt.DisplayRole:
            node.name = value
            return True

        elif role == Qt.CheckStateRole:
            (lowest_row, lowest_parent), (highest_row, highest_parent) = self.tree.set_checked(node, value)
            highest_index = self.createIndex(highest_row, 0, highest_parent)
            lowest_index = self.createIndex(lowest_row, 0, lowest_parent)

            invoke_in_main_thread(self.dataChanged.emit, highest_index, lowest_index, [role])  # unclear why this must be done via events?
            return True

        return False

    def removeRows(self, row: int, count: int, parent: QModelIndex = QModelIndex()) -> bool:
        self.beginRemoveRows(parent, row, row + count - 1)
        for i in reversed(range(row, row + count)):
            node = self.tree.node(i, parent.internalPointer())
            self.tree.remove_node(node)
            # self.setData(self.index(i, 0, parent), Qt.Unchecked, Qt.CheckStateRole)
        self.endRemoveRows()
        return True


class EnsembleModel(TreeModel):

    def __init__(self, parent=None):
        super(EnsembleModel, self).__init__(parent)

        self._active_ensemble = None  # type: Ensemble

    def _ensembleBackground(self, index):
        # Updates the ensemble background (highlight) style based on its active status
        palette = QApplication.palette()
        brush = QBrush()
        if self._active_ensemble == index.internalPointer():
            brush = palette.color(QPalette.Normal, QPalette.Highlight)
        return brush

    def _ensembleForeground(self, index):
        # Updates the ensemble foreground (text color) style based on its active status
        palette = QApplication.palette()
        brush = QBrush()
        if self._active_ensemble == index.internalPointer():
            brush = palette.color(QPalette.Normal, QPalette.BrightText)
        return brush

    def data(self, index: QModelIndex, role=Qt.DisplayRole) -> Any:
        if isinstance(index.internalPointer(), Ensemble):
            if role == Qt.ForegroundRole:
                return self._ensembleForeground(index)
            if role == Qt.BackgroundRole:
                return self._ensembleBackground(index)
        return super(EnsembleModel, self).data(index, role)

    def appendIntent(self, intent: Intent, catalog):
        intent_parent = catalog
        intent_count = self.tree.child_count(catalog)
        intent_parent_index = self.createIndex(intent_count, 0, intent_parent)
        self.insert_and_check(intent_count, intent_parent_index, intent)

    def intents(self, node: Union[BlueskyRun, Ensemble]):
        if isinstance(node, Ensemble):
            return list(itertools.chain(*[self.tree.children(catalog) for catalog in self.tree.children(node)]))
        elif isinstance(node, BlueskyRun):
            return self.tree.children(node)

    def catalogs(self, ensemble: Ensemble = None):
        if not ensemble:
            ensemble = self.activeEnsemble
        return self.tree.children(ensemble)

    def appendCatalog(self, catalog: BlueskyRun, projectors, ensemble: Ensemble = None):
        catalog_parent = ensemble or self.activeEnsemble
        catalog_count = self.tree.child_count(ensemble)
        catalog_parent_index = self.createIndex(catalog_count, 0, catalog_parent)
        self.insert_and_check(catalog_count, catalog_parent_index, catalog)

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
        self.insert_and_check(ensemble_count, parent_index, ensemble)

        # New ensemble will be come the active ensemble
        # Wait until after adding node to tree to set it as active ensemble (since that triggers dataChanged)
        self.activeEnsemble = ensemble

    @property
    def activeEnsemble(self) -> Ensemble:
        return self._active_ensemble

    @activeEnsemble.setter
    def activeEnsemble(self, ensemble):
        """Sets the active ensemble.

        Emits dataChanged on the active ensemble's foreground and background roles,
        so attached view(s) will display active/inactive ensembles properly.
        """
        self._active_ensemble = ensemble
        if self._active_ensemble is not None:
            row, _ = self.tree.index(self._active_ensemble)
            index = self.index(row, 0)
            self.dataChanged.emit(index, index, [Qt.ForegroundRole, Qt.BackgroundRole])

    def removeRows(self, row: int, count: int, parent: QModelIndex = QModelIndex()) -> bool:
        # Need to override TreeModel's implementation to handle when active ensemble is removed
        self.beginRemoveRows(parent, row, row + count - 1)
        active_removed = False
        for i in reversed(range(row, row + count)):
            node = self.tree.node(i, parent.internalPointer())
            if node == self._active_ensemble:
                active_removed = True
            # self.setData(self.index(i, 0, parent), Qt.Unchecked, Qt.CheckStateRole)
            self.tree.remove_node(node)
        self.endRemoveRows()

        if active_removed:
            if self.rowCount() > 0:  # active removed, let's just set it to the most recent ensemble
                self.activeEnsemble = self.index(self.rowCount() - 1, 0).internalPointer()
            else:  # active removed, no ensembles left in tree
                self.activeEnsemble = None
        return True

    def insert_and_check(self, row: int, parent: QModelIndex, node) -> bool:
        self.beginInsertRows(parent, row, row)
        self.tree.add_node(node, parent.internalPointer())
        self.endInsertRows()

        if isinstance(node, Intent):
            self.setData(self.index(row, 0, parent), Qt.Checked, role=Qt.CheckStateRole)
