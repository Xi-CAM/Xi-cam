from typing import Any
from qtpy.QtCore import Qt, QAbstractItemModel, QModelIndex


class TreeItem(object):
    """Qt-agnostic tree item. Follows general API of QStandardItem for compatibility.

    Stores check state integer (can be interfaced with the Qt.CheckState enum).

    Single column support only (right now).
    """
    def __init__(self, parent=None):
        self.parentItem = parent
        self.itemData = {}
        self.childItems = []
        self.checked_state = 0
        # TODO: refactor to not store checked_state (it can be stored in itemData)

    def appendChild(self, item):
        self.childItems.append(item)

    def child(self, row: int):  # -> TreeItem
        if row < 0 or row >= len(self.childItems):
            return None
        return self.childItems[row]

    def childCount(self) -> int:
        return len(self.childItems)

    def columnCount(self) -> int:
        # TODO support multiple columns
        # assert len(self.itemData) == 1
        return len(self.itemData)

    def checkState(self) -> int:
        return self.checked_state

    def data(self, role):
        return self.itemData.get(role)

    def hasChildren(self) -> int:
        return self.childCount() > 0

    def parent(self):  # -> TreeItem
        return self.parentItem

    def row(self) -> int:
        if self.parentItem:
            return self.parentItem.childItems.index(self)

        return 0

    def setCheckState(self, state: int):
        self.checked_state = state

    def setData(self, value: Any, key: int):
        self.itemData[key] = value
        return True
    # def setData(self, column: int, value: Any) -> bool:
    #     if column < 0 or column >= len(self.itemData):
    #         return False
    #     self.itemData[column] = value
    #     return True


class TreeModel(QAbstractItemModel):
    """Qt-based tree model.

    For now, single-column support only
    """
    def __init__(self, parent=None):
        super(TreeModel, self).__init__(parent)

        self._invisibleRootItem = TreeItem()
        self.rootItem = TreeItem(self._invisibleRootItem)
        self.rootItem.setData("Tree Model", Qt.DisplayRole)
        self._invisibleRootItem.appendChild(self.rootItem)

    def invisibleRootItem(self):
        return self._invisibleRootItem

    def columnCount(self, parent: QModelIndex) -> int:
        if parent.isValid():
            return parent.internalPointer().columnCount()
        else:
            return self.rootItem.columnCount()

    def data(self, index: QModelIndex, role=Qt.DisplayRole) -> Any:
        if not index.isValid():
            return None

        item = self.getItem(index)

        if role == Qt.CheckStateRole:
            # checkstate = item.itemData.get(Qt.CheckStateRole)
            # if checkstate is None:
            #     item.itemData[Qt.CheckStateRole] = 0
            # return checkstate

            return item.checkState()

        return item.itemData.get(role)

    def flags(self, index: QModelIndex) -> Qt.ItemFlag:
        if not index.isValid():
            return Qt.NoItemFlags

        return super(TreeModel, self).flags(index) | Qt.ItemIsUserCheckable #|Qt.ItemIsEditable
        #return Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsUserCheckable

    def getItem(self, index: QModelIndex) -> TreeItem:
        if index.isValid():
            item = index.internalPointer()
            if item:
                return item

        return self.rootItem

    def headerData(self, section: int, orientation: Qt.Orientation, role: Qt.ItemDataRole) -> Any:
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self.rootItem.data(section)

        return None

    def index(self, row: int, column: int, parent: QModelIndex = QModelIndex()) -> QModelIndex:
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
        if not index.isValid():
            return QModelIndex()

        childItem = index.internalPointer()
        parentItem = childItem.parent()

        if parentItem == self.rootItem:
            return QModelIndex()

        return self.createIndex(parentItem.row(), 0, parentItem)

    def rowCount(self, parent: QModelIndex) -> int:
        if parent.column() > 0:
            return 0

        if not parent.isValid():
            parentItem = self.rootItem
        else:
            parentItem = parent.internalPointer()

        return parentItem.childCount()

    def _determineCheckState(self, item: TreeItem) -> Qt.CheckState:
        # Return if item should or shouldn't be checked
        # Unchecked -> Checked
        # PartiallyChecked -> Checked
        # Checked -> Unchecked
        if item.checkState() == Qt.Checked:
            return Qt.Unchecked
        else:
            return Qt.Checked

    def _setItemAndChildrenCheckState(self, item: TreeItem, state: Qt.CheckState):
        for row in range(item.childCount()):
            self._setItemAndChildrenCheckState(item.child(row), state)

        item.setCheckState(state)

    def _setParentItemCheckState(self, item: TreeItem, state: Qt.CheckState):
        parent = item.parent()
        sibling_check_states = [parent.child(row).checkState() for row in range(parent.childCount())]
        while parent and parent != self.rootItem:
            if all(check_state == sibling_check_states[0] for check_state in sibling_check_states):
                parent.setCheckState(state)
            else:
                parent.setCheckState(Qt.PartiallyChecked)

            parent = parent.parent()

    def setData(self, index: QModelIndex, value: Any, role: Qt.ItemDataRole = Qt.EditRole) -> bool:
        if not index.isValid():
            return False

        item = self.getItem(index)

        if role == Qt.DisplayRole:
            item.itemData[role] = value
            self.dataChanged.emit(index, index, [role])
            return True

        elif role == Qt.CheckStateRole:
            item_checked = self._determineCheckState(item)
            # Subsequently set all childrens' check states
            self._setItemAndChildrenCheckState(item, item_checked)
            self._setParentItemCheckState(item, item_checked)

            highest_parent_index = index.parent()
            while highest_parent_index.parent().isValid():
                highest_parent_index = highest_parent_index.parent()

            def find_lowest_index(idx):
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

            # self.dataChanged.emit(index, index, [role])
            self.dataChanged.emit(highest_parent_index, lowest_index, [role])
            return True

        elif role == Qt.EditRole:
            index.internalPointer().itemData[index.column()] = value
            self.dataChanged.emit(index, index, [role])
            return True

        else:
            return False


# if __name__ == '__main__':
#
#     # TODO: do we want canvasmanager's bound to a model or view?
#     # (e.g. CanvasProxyModel, EnsembleModel(TreeModel) vs. ResultsView, ResultsSplitView, ...
#
#     from qtpy.QtWidgets import QApplication, QWidget, QHBoxLayout, QTreeView, QPushButton
#
#     from databroker.in_memory import BlueskyInMemoryCatalog
#     from qtpy.QtWidgets import QApplication, QMainWindow, QSplitter, QListView, QTreeView
#     from xicam.XPCS.ingestors import ingest_nxXPCS
#     from xicam.XPCS.models import Ensemble, EnsembleModel
#     from xicam.XPCS.models import CanvasProxyModel
#
#
#     app = QApplication([])
#     window = QWidget()
#
#     uris = ["/home/ihumphrey/Downloads/B009_Aerogel_1mm_025C_att1_Lq0_001_0001-10000.nxs"]
#     document = list(ingest_nxXPCS(uris))
#     uid = document[0][1]["uid"]
#     catalog = BlueskyInMemoryCatalog()
#     catalog.upsert(document[0][1], document[-1][1], ingest_nxXPCS, [uris], {})
#     cat = catalog[uid]
#
#     # model = TreeModel()
#     source_model = EnsembleModel()
#     ensemble = Ensemble()
#     ensemble.append_catalog(cat)
#     source_model.add_ensemble(ensemble)
#     model = source_model
#     proxy = CanvasProxyModel()
#     proxy.setSourceModel(model)
#
#     n_children = 2
#     n_gchildren = 3
#     n_ggchildren = 3
#     for child in range(n_children):
#         child_item = TreeItem(model.rootItem)
#         child_item.setData(f"{child} child", Qt.DisplayRole)
#         for gchild in range(n_gchildren):
#             gchild_item = TreeItem(child_item)
#             gchild_item.setData(f"{gchild} gchild", Qt.DisplayRole)
#             for ggchild in range(n_ggchildren):
#                 ggchild_item = TreeItem(gchild_item)
#                 ggchild_item.setData(f"{ggchild} ggchild", Qt.DisplayRole)
#                 gchild_item.appendChild(ggchild_item)
#             child_item.appendChild(gchild_item)
#         model.rootItem.appendChild(child_item)
#
#     view = QTreeView()
#     view.setModel(model)
#
#     from xicam.SAXS.widgets.views import ResultsViewThing
#     view2 = ResultsViewThing()
#     view2.setModel(proxy)
#
#     def update(*_):
#         ix = model.index(0, 0, QModelIndex())
#         model.setData(ix, "BLAH", Qt.DisplayRole)
#     button = QPushButton()
#     button.clicked.connect(update)
#     layout = QHBoxLayout()
#     layout.addWidget(view)
#     layout.addWidget(view2)
#     layout.addWidget(button)
#
#     window.setLayout(layout)
#     window.setWindowTitle("Simple Tree Model")
#     window.show()
#
#     app.exec_()