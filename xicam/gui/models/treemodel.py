from collections import defaultdict
from typing import Any, List, Tuple, Union

from databroker.core import BlueskyRun
from qtpy.QtCore import Qt, QAbstractItemModel, QModelIndex, QItemSelectionModel
from xicam.core.intents import Intent
from xicam.core.workspace import Ensemble


class Tree:
    def __init__(self):
        super(Tree, self).__init__()
        self._parent_mapping = dict()
        self._child_mapping = defaultdict(list)

    def add_node(self, node: object, parent=None):
        self.insert_node(node, row=len(self._child_mapping[node]) + 1, parent=parent)

    def insert_node(self, node: object, row: int, parent=None):
        self._parent_mapping[node] = parent
        self._child_mapping[parent].insert(row, node)

    def children(self, node: object) -> List[object]:
        return self._child_mapping[node]

    def parent(self, node: object) -> object:
        return self._parent_mapping[node]

    def remove_node(self, node: object, drop_children=True):
        children = self.children(node)
        if children and not drop_children:
            raise RuntimeError('Cannot remove node; it has children!')
        for child in children:
            self.remove_node(child)
        del self._parent_mapping[node]
        del self._child_mapping[node]

    def index(self, node: object) -> Tuple[int, object]:
        parent = self._parent_mapping[node]
        row = self._child_mapping[parent].index(node)
        return row, parent

    def node(self, row, parent=None) -> object:
        return self._child_mapping[parent][row]

    def __contains__(self, item):
        return item in self._parent_mapping

    # Non-critical convenience methods
    def child_count(self, node: object) -> int:
        return len(self._child_mapping[node])

    def has_children(self, node: object) -> bool:
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

    def set_checked(self, node: object, value: Union[Qt.Checked, Qt.Unchecked, Qt.PartiallyChecked]) -> Tuple[Tuple[int, object], Tuple[int, object]]:
        lowest_node = self._check_recurse_down(node, value)
        highest_node = self._check_recurse_up(node)
        return self.index(lowest_node), self.index(highest_node)

    def _check_recurse_down(self, node: object, value: Union[Qt.Checked, Qt.Unchecked, Qt.PartiallyChecked]) -> object:
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
        if parent is None: return
        siblings_checked = list(map(self.checked, self.children(node)))
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

    def remove_node(self, node: object, drop_children=True) -> Tuple[int, object]:
        del self._checked[node]
        highest_node = self._check_recurse_up(node)
        super(CheckableTree, self).remove_node(node, drop_children)
        return self.index(highest_node)


class TreeModel(QAbstractItemModel):
    """Qt-based tree model.

    For now, single-column support only.

    This tree model is an AbstractItem model that is designed to contain (not QStandardItems).
    Two important caveats regarding this:
    1. We cannot defer to super(...).setData(...) in setData, since the parent implementation always returns False
    2. We must update the generic items' data via a private _setData call, which then emits a dataChanged signal
    """

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
        elif isinstance(node, BlueskyRun):
            if role == Qt.DisplayRole:
                return node.name  # TODO: probably needs to be something else here
        elif isinstance(node, Intent):
            if role == Qt.DisplayRole:
                return node.name
            if role == Qt.CheckStateRole:
                return self.intent_selection_model.isSelected(index)

        return None

    def flags(self, index: QModelIndex) -> Qt.ItemFlag:
        """Re-implement to additionally ensure that this model is checkable."""
        if not index.isValid():
            # return Qt.NoItemFlags
            return super(TreeModel, self).flags(index)

        return Qt.ItemIsEditable

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

        return self.createIndex(parent_row, 0, parents_parent)

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

    def _setData(self, index, value, role) -> bool:
        """Internal setData that sets the generic TreeItem's itemData attribute
        and emits a dataChanged.

        This is used because QAbstractItemModel.setData() always returns False,
        and we are using generic items (not QStandardItems).
        """

        item = self.getItem(index)
        item.setData(value, role)
        self.dataChanged.emit(index, index, [role])
        return True

    def setData(self, index: QModelIndex, value: Any, role: Qt.ItemDataRole = Qt.EditRole) -> bool:
        """Re-implemented to set the associated item's itemData property and emit dataChanged.

        Special case for CheckStateRole handles checking of all children (recursively)
        and all ancestors to appropriate check states (including PartiallyChecked states).

        Returns True if the data was successfully set.
        """
        if not index.isValid():
            return False

        node = index.internalPointer()

        if role == Qt.CheckStateRole:
            (lowest_row, lowest_parent), (highest_row, highest_parent) = self.tree.set_checked(node, value)
            highest_index = self.createIndex(highest_row, 0, highest_parent)
            lowest_index = self.createIndex(lowest_row, 0, lowest_parent)

            self.dataChanged.emit(highest_index, lowest_index, [role])
            return True

        else:
            return self._setData(index, value, role)

    def removeRows(self, row: int, count: int, parent: QModelIndex = QModelIndex()) -> bool:
        if not parent.isValid():
            return False

        self.beginRemoveRows(parent, row, row + count - 1)
        for i in reversed(range(row, count + 1)):
            node = self.tree.node(i, parent.internalPointer())
            self.tree.remove_node(node)
        self.endRemoveRows()

        # TODO: right now, intents are cleared then re-added via IntentsModel and CanvasView,
        #  so, indexes emitted here aren't important (for now)
        self.dataChanged.emit(QModelIndex(), QModelIndex(), [Qt.CheckStateRole])
        return True
