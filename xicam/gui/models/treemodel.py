from typing import Any
from qtpy.QtCore import Qt, QAbstractItemModel, QModelIndex


class TreeItem:
    """Qt-agnostic tree item. Mocks the general API of QStandardItem for compatibility.

    Stores check state integer (can be interfaced with the Qt.CheckState enum).
    Single column support only (right now).

    Parameters
    ----------
    parent: TreeItem
        Parent TreeItem for the item you are creating.
        All TreeItems should have a parent except for the root/header item.
        Default is None.
    """
    def __init__(self, parent=None):
        self.parentItem = parent
        self._itemData = {}
        self.childItems = []
        self._flags = Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsUserCheckable
        # All TreeItems will have a parent unless it is the root (header) item.
        # Header item will not get a check state role applied to it.
        if parent:
            self.setData(Qt.Unchecked, Qt.CheckStateRole)

    def appendChild(self, item):
        self.childItems.append(item)

    def child(self, row: int):  # -> TreeItem
        if row < 0 or row >= len(self.childItems):
            return None
        return self.childItems[row]

    def childCount(self) -> int:
        return len(self.childItems)

    def columnCount(self) -> int:
        return 1
        # TODO support multiple columns
        # assert len(self.itemData) == 1
        # return len(self.itemData)

    def data(self, role):
        return self._itemData.get(role)

    def hasChildren(self) -> int:
        return self.childCount() > 0

    def parent(self):  # -> TreeItem
        return self.parentItem

    def removeChildren(self, row: int, count: int) -> bool:
        # Bad remove (out of bounds), return False
        if row < 0 or row + count > self.childCount():
            return False

        for child in range(row, row + count):
            del self.childItems[child]

        return True

    def row(self) -> int:
        if self.parentItem:
            return self.parentItem.childItems.index(self)

        return 0

    def setData(self, value: Any, key: int):
        """Mimics QStandardItem.setData(value, role).

        Pass in a value and key, maps as key -> role
        Internally sets the itemData's key (role) to the passed value.
        """
        self._itemData[key] = value
        return True

    def flags(self):
        return Qt.ItemFlag(self._flags)

    def setFlags(self, flags):
        self._flags = flags


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

        # Create a private invisible root item at the top of the tree, with an accessible child rootItem
        # TODO: i don't think we need the invisibleRootItem or its accessor method
        self._invisibleRootItem = TreeItem()
        self.rootItem = TreeItem(self._invisibleRootItem)
        self.rootItem.setData("Tree Model", Qt.DisplayRole)
        self._invisibleRootItem.appendChild(self.rootItem)

    def invisibleRootItem(self):
        # TODO: this is unused, remove
        return self._invisibleRootItem

    def columnCount(self, index: QModelIndex) -> int:
        """Returns the number of columns in the given index."""
        if index.isValid():
            return index.internalPointer().columnCount()
        # For an invalid index, return the number of columns defined at the root item of the tree
        else:
            return self.rootItem.columnCount()

    def data(self, index: QModelIndex, role=Qt.DisplayRole) -> Any:
        # TODO: this is probably not necessary; since the checkstate can be set/accessed via the item.itemData dict
        """Returns the data of the index with the associated role.
        """
        if not index.isValid():
            return None

        item = self.getItem(index)
        return item.data(role)

    def flags(self, index: QModelIndex) -> Qt.ItemFlag:
        """Re-implement to additionally ensure that this model is checkable."""
        if not index.isValid():
            # return Qt.NoItemFlags
            return super(TreeModel, self).flags(index)

        return self.getItem(index).flags()

        # return super(TreeModel, self).flags(index) #| Qt.ItemIsUserCheckable | Qt.ItemIsEditable
        #return Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsUserCheckable

    def getItem(self, index: QModelIndex) -> TreeItem:
        """Convenience method to get a TreeItem from a given index.

        Returns the root item if the index passed is not valid."""
        if index.isValid():
            item = index.internalPointer()
            if item:
                return item

        return self.rootItem

    def headerData(self, section: int, orientation: Qt.Orientation, role: Qt.ItemDataRole) -> Any:
        """Define a horizontal header that uses the root item's DisplayRole to populate its data."""
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self.rootItem.data(section)

        return None

    def index(self, row: int, column: int, parent: QModelIndex = QModelIndex()) -> QModelIndex:
        """Re-implement the index method to appropriately handle tree-like models.

        Returns an invalid (default-constructed) index if hasIndex fails,
        or if the parent index passed does not have any children.
        """
        if not self.hasIndex(row, column, parent):
            return QModelIndex()

        if not parent.isValid():
            parentItem = self.rootItem
        else:
            parentItem = parent.internalPointer()

        childItem = parentItem.child(row)
        if childItem:
            return self.createIndex(row, column, childItem)
        else:
            return QModelIndex()

    def parent(self, index: QModelIndex) -> QModelIndex:
        """Re-implemented to return an invalid index if the index passed's parent is the root item.

        In other words, an index whose parent is the root item does not have a user/view accessible parent.
        """
        if not index.isValid():
            return QModelIndex()

        childItem = index.internalPointer()
        parentItem = childItem.parent()

        if parentItem == self.rootItem:
            return QModelIndex()

        return self.createIndex(parentItem.row(), 0, parentItem)

    def rowCount(self, index: QModelIndex = QModelIndex()) -> int:
        """If an invalid index is passed, returns the childCount of the root item;
        otherwise, returns the index's childCount.
        """

        # supports only single-column data
        if index.column() > 0:
            return 0

        if not index.isValid():
            parentItem = self.rootItem
        else:
            parentItem = index.internalPointer()

        return parentItem.childCount()

    def _determineCheckState(self, item: TreeItem) -> Qt.CheckState:
        """Return if item should or shouldn't be checked.

        When an item is currently checked, it should become unchecked when interacted with by a user/view.
        Otherwise, the item should be checked. (children handled in separate methods, see below)
        """

        if item.data(Qt.CheckStateRole) == Qt.Checked:
            return Qt.Unchecked
        else:
            return Qt.Checked

    def _setItemAndChildrenCheckState(self, item: TreeItem, state: Qt.CheckState):
        """Set the item's check state and its children (recursively) to the given state."""
        for row in range(item.childCount()):
            self._setItemAndChildrenCheckState(item.child(row), state)

        item.setData(state, Qt.CheckStateRole)

    def _setParentItemCheckState(self, item: TreeItem, state: Qt.CheckState):
        """Set the item's ancestors check state to the given state.

        This will handle either setting the ancestors to Checked or PartiallyChecked,
        depending on the childrens' check states.
        """
        parent = item.parent()
        sibling_check_states = [parent.child(row).data(Qt.CheckStateRole) for row in range(parent.childCount())]
        while parent and parent != self.rootItem:
            if all(check_state == sibling_check_states[0] for check_state in sibling_check_states):
                parent.setData(state, Qt.CheckStateRole)
            else:
                if parent.data(Qt.CheckStateRole) != Qt.PartiallyChecked:
                    parent.setData(Qt.PartiallyChecked, Qt.CheckStateRole)

            parent = parent.parent()

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

        item = self.getItem(index)

        if role == Qt.CheckStateRole:
            item_checked = self._determineCheckState(item)
            # Subsequently set all childrens' check states
            self._setItemAndChildrenCheckState(item, item_checked)
            self._setParentItemCheckState(item, item_checked)

            highest_parent_index = index.parent()
            while highest_parent_index.parent().isValid():
                highest_parent_index = highest_parent_index.parent()

            def find_lowest_index(idx):
                if not idx.isValid():
                    return idx

                itm = self.getItem(idx)
                if itm.hasChildren():
                    lowest_child_index = self.index(item.childCount() - 1, 0, idx)
                    find_lowest_index(lowest_child_index)
                return idx

                lowest_sibling_index = idx.siblingAtRow(itm.parent().childCount() - 1)
                if self.getItem(lowest_sibling_index).hasChildren():
                    find_lowest_index(lowest_sibling_index)
                else:
                    return lowest_sibling_index

            lowest_index = find_lowest_index(index)

            self.dataChanged.emit(highest_parent_index, lowest_index, [role])
            return True

        else:
            return self._setData(index, value, role)

    def removeRows(self, row: int, count: int, parent: QModelIndex = QModelIndex()) -> bool:

        parent_item = self.getItem(parent)
        if parent_item is None:
            return False
        # beginRemoveRows important for communicating with views (via rowsAboutToBeRemoved sig it emits)
        #  note: rowsAboutToBeRemoved not being used;
        #        we are using this dataChanged -> IntentsModel.dataChanged -> CanvasView.dataChanged
        self.beginRemoveRows(parent, row, row + count - 1)
        removed = parent_item.removeChildren(row, count)
        self.endRemoveRows()

        # TODO: right now, intents are cleared then re-added via IntentsModel and CanvasView,
        #  so, indexes emitted here aren't important (for now)
        self.dataChanged.emit(QModelIndex(), QModelIndex(), [Qt.CheckStateRole])
        return removed
