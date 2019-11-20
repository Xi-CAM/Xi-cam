"""
Catalog Plugin for browsing pre-configured databroker catalogs
"""
from databroker import MergedCatalog
from xicam.plugins.catalogplugin import CatalogPlugin
from xicam.gui.widgets.dataresourcebrowser import QListView
from databroker.core import BlueskyRun
from databroker.v2 import Broker
from intake.catalog import Catalog
from intake.catalog.base import RemoteCatalog
from qtpy.QtCore import Signal
from qtpy.QtWidgets import QWidget, QVBoxLayout
import logging

from xicam.gui.bluesky.central import CentralWidget

# from bluesky_browser.frameworks.qt.main import CentralWidget

logger = logging.getLogger('BlueskyPlugin')


class SearchingCatalogController(QWidget):
    """
    Displays code that lets a user select from a root catalog.


    """

    sigOpen = Signal(object)
    sigSelectedRun = Signal([list])
    sigPreview = Signal(BlueskyRun)
    catalog = None

    def __init__(self, root_catalog):
        """
          The root catalog can be a single catalog or a collection of catalogs.
            Check out https://nsls-ii.github.io/databroker/v2/user/index.htmll#find-a-catalog. This
            class is intended to guide a user to select a catalog from the list in root catalog,
            then inspect and possibly open a selected run catalog.

        :param root_catalog: top level catalog that might contain more catalogs
        """
        super(SearchingCatalogController, self).__init__()

        layout = QVBoxLayout()
        self.setLayout(layout)

        layout.setContentsMargins(0, 0, 0, 0)
        self.centralWidget = CentralWidget(menuBar=None, catalog=root_catalog)

        def emit_opened_catalogs(name, my_list):
            """Emit each selected and opened catalog to sigOpen"""
            [self.sigOpen.emit(item) for item in my_list]

        # connect the open_entries in the search model to sigOpen
        self.centralWidget.search_model.open_entries.connect(emit_opened_catalogs)
        self.centralWidget.summary_widget.open.connect(emit_opened_catalogs)
        layout.addWidget(self.centralWidget)


class DatabrokerCatalogPlugin(CatalogPlugin):
    """
    Plugin for providing a user interface for browsing and selecting databroker
    catalogs. Users can select one or more catalogs in a list, which will signal
    to xi-cam sigOpen.
    """

    # set name here so that it appears in the catalog dropdown
    name = 'Bluesky Databroker'

    def __new__(cls):
        # importing catalog gives us #a catalog of pre-configured catalogs YAML files
        # locations by default might look something like:
        #  'USER_HOME/.local/share/intake', 'PYTHON_ENV/share/intake'
        from databroker import catalog
        # normalizedCatalogs = []
        # assemble_catalogs(normalizedCatalogs, catalog)

        # set name again because CatalogPlugins also inherit from Catalog, and that by
        # default not have a name
        # mergedCatalog = MergedCatalog(normalizedCatalogs)
        # mergedCatalog.controller = SearchingCatalogController(mergedCatalog)
        # mergedCatalog.view = QListView()
        # mergedCatalog.name = 'Bluesky Databroker'
        # return mergedCatalog

        '''
        Hard-coded to read from a yaml source named 'intake_server' for testing.
        
        '''
        catalog.controller = SearchingCatalogController(catalog)
        catalog.view = QListView()
        catalog.name = 'Bluesky Databroker'
        return catalog

# def assemble_catalogs(normalizedCatalogs, parentCatalog):
#     '''
#      create a dict of only top level catalogs...parents of BlueskyRun
#     :param normalizedCatalog:
#     :param databrokerCatalogs:
#     :return:
#     '''
#
#     for catalogName in parentCatalog:
#         catalogEntry = parentCatalog[catalogName]
#         catalog = catalogEntry.get()
#         if isinstance(catalog, Broker):
#             # this test fails because when coming from intake,
#             # the parent of BlueSkyRuns is a RemoteCatalog, not a Broker
#             normalizedCatalogs.append(catalog)
#             continue
#         elif isinstance(catalog, Catalog):
#             assemble_catalogs(normalizedCatalogs, catalog)
#         else:
#             continue

