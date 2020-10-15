from pytestqt import qtbot
from xicam.gui.widgets.metadataview import MetadataView
from qtpy.QtGui import QStandardItemModel, QStandardItem
from qtpy.QtCore import QItemSelectionModel, Qt
from xicam.core.tests.fixtures import catalog


def test_metadataview(qtbot, catalog):
    catalogmodel = QStandardItemModel()
    selectionmodel = QItemSelectionModel()
    selectionmodel.setModel(catalogmodel)

    item = QStandardItem()
    item.setData('test catalog', Qt.DisplayRole)
    item.setData(catalog, Qt.UserRole)
    catalogmodel.appendRow(item)
    catalogmodel.dataChanged.emit(item.index(), item.index())

    selectionmodel.setCurrentIndex(catalogmodel.indexFromItem(item), selectionmodel.SelectCurrent)

    w = MetadataView(catalogmodel, selectionmodel)
    w.show()
