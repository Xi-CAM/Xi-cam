import itertools
from .plugin import PluginType
from qtpy.QtWidgets import QListView, QWidget, QVBoxLayout
from qtpy.QtCore import Signal, QAbstractItemModel, QModelIndex, Qt, QObject
from intake.catalog.base import Catalog
from xicam.core import msg
from collections import OrderedDict


# from intake_bluesky.in_memory import SafeLocalCatalogEntry


class CatalogModel(QAbstractItemModel):
    """
    This model binds to a Catalog, and represents its contents in a paginated way, configurable by `pagination_size`

    Its expected use is either
    - uniquely bound to a static Catalog
    - dynamically rebound to catalogs (i.e. as a datasource is filtered) with `.setCatalog`
    """

    pagination_size = 10

    def __init__(self, catalog: Catalog):
        self.catalog = catalog
        super(CatalogModel, self).__init__()

        # Note: both of these caches are used so that indexing by row is performant
        # A cache of the RunCatalogs seen by this model
        self._cache = []

        # For iterating over the catalog as needed
        self._run_iterator = self.catalog.__iter__()

        # This model will add items to itself at the request any view
        self._rowcount = 0

    def index(self, row, column, parent):
        return self.createIndex(row, column)

    def parent(self, index):
        return QModelIndex()

    def rowCount(self, index):
        return self._rowcount

    def columnCount(self, index):
        return 1

    def data(self, index, role=Qt.DisplayRole):
        if role == Qt.DisplayRole:
            return self._cache[index.row()].name

    def canFetchMore(self, parent):
        if parent.isValid():
            return False
        return self._rowcount < len(self.catalog)

    def fetchMore(self, parent):
        if parent.isValid():
            return

        # prevent fetching more items than the catalog currently has
        to_fetch = min(len(self.catalog) - self._rowcount, self.pagination_size)

        # print(f'Fetching next {to_fetch} runs')

        # pre-fetch more uids from the datasource
        new_uids = itertools.islice(self._run_iterator, to_fetch)

        # fetch more RunCatalogs from the datasource
        self._cache.extend(self.catalog[uid] for uid in new_uids)

        self.beginInsertRows(QModelIndex(), self._rowcount, self._rowcount + to_fetch)
        self._rowcount += to_fetch  # Tell the model it now has more rows
        self.endInsertRows()

    # NOTE: the following methods are expected to be called by an external controller

    def setCatalog(self, catalog):
        self.catalog = catalog
        self.reset()

    def reset(self):
        self._cache = []
        self._rowcount = 0
        self._run_iterator = self.catalog.__iter__()


class CatalogController(QWidget):
    # TODO: Make a desicion what we want these signal objects to be
    sigOpen = Signal(object)
    # TODO: Make sure these are emitted / connected
    sigPreview = Signal(object)

    sigOpenPath = Signal(str)
    sigOpenExternally = Signal(str)
    # TODO: Emit original / new str
    sigLocationChanged = Signal()

    def __init__(self, view, parent=None):
        super(CatalogController, self).__init__(parent=parent)
        self.setLayout(QVBoxLayout())
        self.layout().addWidget(view)

        self.view = view

        # Setup signal emissions
        view.doubleClicked.connect(self.open)

    def open(self, _):
        indexes = self.view.selectionModel().selectedRows()

        runs = [self.view.model().catalog[self.view.model().data(index)] for index in indexes]

        for run in runs:
            self.sigOpen.emit(run)


class CatalogPlugin(Catalog, PluginType):
    is_singleton = False
    needs_qt = True
    name = ""

    model = CatalogModel
    view = QListView
    controller = CatalogController

    def __init__(self, *args, **kwargs):
        super(CatalogPlugin, self).__init__()
        self.setup()

    def setup(self):
        import inspect

        if inspect.isclass(self.model):
            self.model = self.model(self)

        if inspect.isclass(self.view):
            self.view = self.view()
            self.view.setModel(self.model)

        if inspect.isclass(self.controller):
            self.controller = self.controller(self.view)


if __name__ == "__main__":
    from intake_bluesky.jsonl import BlueskyJSONLCatalog
    import glob

    class JSONLCatalogPlugin(BlueskyJSONLCatalog, CatalogPlugin):
        ...

    from qtpy.QtWidgets import QApplication

    qapp = QApplication([])

    paths = glob.glob("/home/rp/data/Catalog Sample/abc/*.jsonl")
    model = JSONLCatalogPlugin(paths).model

    view = QListView()
    view.setModel(model)

    view.show()
    qapp.exec_()
