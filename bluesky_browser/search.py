"""
Experimental Qt-based data browser for bluesky
"""
import itertools
import logging
import time

from qtpy.QtCore import QDateTime, Qt
from qtpy.QtGui import QStandardItemModel, QStandardItem
from qtpy.QtWidgets import (
    QApplication,
    QCalendarWidget,
    QDateTimeEdit,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QVBoxLayout,
    QWidget,
    QTableView,
    )
import intake_bluesky.mongo_normalized  # noqa; to force intake registration


MAX_SEARCH_RESULTS = 100


log = logging.getLogger('bluesky_browser')

class SearchState:
    """
    Encapsulates CatalogSelectionModel and SearchResultsModel. Executes search.
    """
    def __init__(self, catalog, search_result_row):
        self.catalog = catalog
        self.search_result_row = search_result_row
        self.catalog_selection_model = CatalogSelectionModel()
        self.search_results_model = SearchResultsModel(self)

    def list_subcatalogs(self):
        self.catalog_selection_model.clear()
        for name, entry in self.catalog.items():
            self.catalog_selection_model.appendRow(QStandardItem(str(name)))

    def search(self):
        self.search_results_model.clear()
        query = {'time': {}}
        if self.search_results_model.since is not None:
            query['time']['$gte'] = self.search_results_model.since
        if self.search_results_model.until is not None:
            query['time']['$lt'] = self.search_results_model.until
        query.update(**self.search_results_model.custom_query)
        results = self.catalog.search(query)
        log.debug('Query %r -> %d results', query, len(results))
        for uid, entry in itertools.islice(results.items(), MAX_SEARCH_RESULTS):
            row = []
            for text in self.search_result_row(entry).values():
                item = QStandardItem(text or '')
                row.append(item)
            self.search_results_model.appendRow(row)
        try:
            _, entry = next(iter(results.items()))
        except StopIteration:
            pass
        else:
            self.search_results_model.setHorizontalHeaderLabels(
                list(self.search_result_row(entry)))


class CatalogSelectionModel(QStandardItemModel):
    """
    List the subcatalogs in the root Catalog.
    """
    ...


class SearchResultsModel(QStandardItemModel):
    """
    Perform searches on a Catalog and model the results.
    """
    def __init__(self, search_state, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.custom_query = {}
        self.search_state = search_state
        self.since = None
        self.until = None

    def on_search_text_changed(self, text):
        try:
            self.custom_query = eval("dict({})".format(text))
        except Exception:
            return
        self.search_state.search()

    def on_since_time_changed(self, datetime):
        self.since = datetime.toSecsSinceEpoch()
        self.search_state.search()

    def on_until_time_changed(self, datetime):
        self.until = datetime.toSecsSinceEpoch()
        self.search_state.search()


class SearchInputWidget(QWidget):
    """
    Input fields for specifying searches on SearchResultsModel
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.search_bar = QLineEdit()

        self.since_widget = QDateTimeEdit()
        self.since_widget.setCalendarPopup(True)
        self.since_widget.setDisplayFormat('yyyy-MM-dd HH:mm')
        since_layout = QHBoxLayout()
        since_layout.addWidget(QLabel('Since:'))
        since_layout.addWidget(self.since_widget)

        self.until_widget = QDateTimeEdit()
        self.until_widget.setCalendarPopup(True)
        self.until_widget.setDisplayFormat('yyyy-MM-dd HH:mm')
        until_layout = QHBoxLayout()
        until_layout.addWidget(QLabel('Until:'))
        until_layout.addWidget(self.until_widget)

        layout = QVBoxLayout()
        layout.addWidget(self.search_bar)
        layout.addLayout(since_layout)
        layout.addLayout(until_layout)
        self.setLayout(layout)


class SearchResultsWidget(QTableView):
    """
    Table of search results
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setSortingEnabled(True)
        self.setSelectionBehavior(QTableView.SelectRows)
        self.setShowGrid(False)
        self.verticalHeader().setVisible(False)
        self.horizontalHeader().setDefaultAlignment(Qt.AlignHCenter)


class SearchWidget(QWidget):
    """
    Search input and results list
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.search_input_widget = SearchInputWidget()
        self.search_results_widget = SearchResultsWidget()

        layout = QVBoxLayout()
        layout.addWidget(self.search_input_widget)
        layout.addWidget(self.search_results_widget)
        self.setLayout(layout)
