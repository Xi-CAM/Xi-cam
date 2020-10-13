from pytestqt import qtbot
from pytest import fixture
from xicam.gui.widgets.metadataview import MetadataView
from qtpy.QtGui import QStandardItemModel, QStandardItem
from qtpy.QtCore import QItemSelectionModel, Qt
from xicam.core.data import load_header

@fixture
def catalog():
    # FIXME: don't rely on a specific absolute path here!
    filepath = "C:\\Users\\LBL\\PycharmProjects\\merged-repo\\Xi-cam.NCEM\\tests\\twoDatasets.emd"
    return load_header([filepath])


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

    qtbot.stopForInteraction()