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
    QComboBox,
    QDateTimeEdit,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QVBoxLayout,
    QWidget,
    QTableView,
    )


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
        self._subcatalogs = []  # to support lookup by item's positional index
        self._results = []  # to support lookup by item's positional index
        self.list_subcatalogs()
        self.set_selected_catalog(0)

    def list_subcatalogs(self):
        self._subcatalogs.clear()
        self.catalog_selection_model.clear()
        for name in self.catalog:
            self._subcatalogs.append(name)
            self.catalog_selection_model.appendRow(QStandardItem(str(name)))

    def set_selected_catalog(self, item):
        name = self._subcatalogs[item]
        self.selected_catalog = self.catalog[name]
        self.search()

    def get_entry_by_item(item):
        """Lookup entry by positional index in listing."""
        return self._results[item]

    def search(self):
        self._results.clear()
        self.search_results_model.clear()
        query = {'time': {}}
        if self.search_results_model.since is not None:
            query['time']['$gte'] = self.search_results_model.since
        if self.search_results_model.until is not None:
            query['time']['$lt'] = self.search_results_model.until
        query.update(**self.search_results_model.custom_query)
        results = self.selected_catalog.search(query)
        log.debug('Query %r -> %d results', query, len(results))
        for uid, entry in itertools.islice(results.items(), MAX_SEARCH_RESULTS):
            row = []
            for text in self.search_result_row(entry).values():
                self._results.append(entry)
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


class CatalogSelectionWidget(QComboBox):
    """
    List of subcatalogs
    """
    ...


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

        self.catalog_selection_widget = CatalogSelectionWidget()
        self.search_input_widget = SearchInputWidget()
        self.search_results_widget = SearchResultsWidget()

        layout = QVBoxLayout()
        layout.addWidget(self.catalog_selection_widget)
        layout.addWidget(self.search_input_widget)
        layout.addWidget(self.search_results_widget)
        self.setLayout(layout)
