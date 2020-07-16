"""
Catalog Plugin for browsing pre-configured databroker catalogs
"""
from xicam.plugins.catalogplugin import CatalogPlugin
from xicam.gui.widgets.dataresourcebrowser import QListView
from databroker.core import BlueskyRun
from qtpy.QtCore import Signal
from qtpy.QtWidgets import QPushButton, QVBoxLayout, QWidget
import logging

from stream_widgets.components.search.searches import Search
from stream_widgets.qt.searches import QtSearch

logger = logging.getLogger("BlueskyPlugin")

# To customize what is displayed in the table of search results, manipulate
# headings and extract_results_row_from_run, which are combined into a tuple
# named columns defined below.

# The length of heading must match the length of the return value from
# extract_results_row_from_run.

headings = (
    "Unique ID",
    "Transient Scan ID",
    "Plan Name",
    "Start Time",
    "Duration",
    "Exit Status",
)


def extract_results_row_from_run(run):
    """
    Given a BlueskyRun, format a row for the table of search results.
    """
    from datetime import datetime

    metadata = run.describe()["metadata"]
    start = metadata["start"]
    stop = metadata["stop"]
    start_time = datetime.fromtimestamp(start["time"])
    if stop is None:
        str_duration = "-"
    else:
        duration = datetime.fromtimestamp(stop["time"]) - start_time
        str_duration = str(duration)
        str_duration = str_duration[: str_duration.index(".")]
    return (
        start["uid"][:8],
        start.get("scan_id", "-"),
        start.get("plan_name", "-"),
        start_time.strftime("%Y-%m-%d %H:%M:%S"),
        str_duration,
        "-" if stop is None else stop["exit_status"],
    )


columns = (headings, extract_results_row_from_run)


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

        search_model = Search(root_catalog, columns=columns)
        self.centralWidget = QtSearch(search_model)

        # Add a button that does something with the currently-selected Runs
        # when you click it.
        open_button = QPushButton("Open")

        def on_click():
            for uid, run in search_model.selection_as_catalog.items():
                self.sigOpen.emit(run)

        def preview_entry(name, catalog: BlueskyRun):
            self.sigPreview.emit(catalog)

        # connect the open_entries in the search model to sigOpen
        open_button.clicked.connect(on_click)

        # self.centralWidget.search_model.preview_entry.connect(preview_entry)
        layout.addWidget(self.centralWidget)
        layout.addWidget(open_button)


class DatabrokerCatalogPlugin(CatalogPlugin):
    """
    Plugin for providing a user interface for browsing and selecting databroker
    catalogs. Users can select one or more catalogs in a list, which will signal
    to xi-cam sigOpen.
    """

    # set name here so that it appears in the catalog dropdown
    name = "Databroker"

    def __new__(cls):
        # importing catalog gives us #a catalog of pre-configured catalogs YAML files
        # locations by default might look something like:
        #  'USER_HOME/.local/share/intake', 'PYTHON_ENV/share/intake'
        from databroker import catalog

        catalog.controller = SearchingCatalogController(catalog)
        catalog.view = QListView()
        catalog.name = "Databroker"
        return catalog
