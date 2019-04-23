"""
Experimental Qt-based data browser for bluesky
"""
import itertools
import logging
import time

from intake.catalog.base import Catalog
from qtpy.QtCore import QDateTime, QObject, Qt, Signal
from qtpy.QtGui import QStandardItemModel, QStandardItem
from qtpy.QtWidgets import (
    QApplication,
    QPushButton,
    QCalendarWidget,
    QComboBox,
    QDateTimeEdit,
    QHBoxLayout,
    QMessageBox,
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
            self._results.append(entry)
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
    selected_result_signal = Signal([list])

    def __init__(self, search_state, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.custom_query = {}
        self.search_state = search_state
        self.since = None
        self.until = None

    def emit_selected_result_signal(self, selected, deselected):
        rows = set(index.row() for index in selected.indexes())
        self.selected_result_signal.emit(
            [self.search_state._results[row] for row in rows])

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
        search_bar_layout = QHBoxLayout()
        search_bar_layout.addWidget(QLabel('Custom Query:'))
        search_bar_layout.addWidget(self.search_bar)
        mongo_query_help_button = QPushButton()
        mongo_query_help_button.setText('?')
        search_bar_layout.addWidget(mongo_query_help_button)
        mongo_query_help_button.clicked.connect(self.show_mongo_query_help)

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
        layout.addLayout(since_layout)
        layout.addLayout(until_layout)
        layout.addLayout(search_bar_layout)
        self.setLayout(layout)

    def show_mongo_query_help(self):
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Information)
        msg.setText("For advanced search capability, enter a valid Mongo query.")
        msg.setInformativeText("""
Examples:

{'plan_name': 'scan'}
{'proposal': 1234},
{'$and': ['proposal': 1234, 'sample_name': 'Ni']}
""")
        msg.setWindowTitle("Custom Mongo Query")
        msg.setStandardButtons(QMessageBox.Ok)
        msg.exec_()


class CatalogList(QComboBox):
    """
    List of subcatalogs
    """
    ...


class CatalogSelectionWidget(QWidget):
    """
    Input widget for selecting a subcatalog
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.catalog_list = CatalogList()
        layout = QHBoxLayout()
        layout.addWidget(QLabel("Catalog:"))
        layout.addWidget(self.catalog_list)
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

        self.catalog_selection_widget = CatalogSelectionWidget()
        self.search_input_widget = SearchInputWidget()
        self.search_results_widget = SearchResultsWidget()

        layout = QVBoxLayout()
        layout.addWidget(self.catalog_selection_widget)
        layout.addWidget(self.search_input_widget)
        layout.addWidget(self.search_results_widget)
        self.setLayout(layout)
