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


class SearchResultsModel(QStandardItemModel):
    """
    Perform searches on a Catalog and model the results.
    """
    def __init__(self, *args, catalog, search_result_row, **kwargs):
        super().__init__(*args, **kwargs)
        self.catalog = catalog
        self.search_result_row = search_result_row
        self.custom_query = {}
        self.since = None
        self.until = None

    def search(self):
        self.clear()
        query = {'time': {}}
        if self.since is not None:
            query['time']['$gte'] = self.since
        if self.until is not None:
            query['time']['$lt'] = self.until
        query.update(**self.custom_query)
        results = self.catalog.search(query)
        log.debug('Query %r -> %d results', query, len(results))
        for uid, entry in itertools.islice(results.items(), MAX_SEARCH_RESULTS):
            row = []
            for text in self.search_result_row(entry).values():
                item = QStandardItem(text or '')
                row.append(item)
            self.appendRow(row)
        if results.items():
            _, entry = next(iter(results.items()))
            self.setHorizontalHeaderLabels(list(self.search_result_row(entry)))

    def on_search_text_changed(self, text):
        try:
            self.custom_query = eval("dict({})".format(text))
        except Exception:
            return
        self.search()

    def on_since_time_changed(self, datetime):
        self.since = datetime.toSecsSinceEpoch()
        self.search()

    def on_until_time_changed(self, datetime):
        self.until = datetime.toSecsSinceEpoch()
        self.search()


class SearchInputWidget(QWidget):
    """
    Input fields for specifying searches on SearchResultsModel
    """
    def __init__(self, *args, search_results_model, **kwargs):
        super().__init__(*args, **kwargs)
        self.search_bar = QLineEdit()

        now = time.time()
        ONE_WEEK = 60 * 60 * 24 * 7

        self.since_widget = QDateTimeEdit()
        self.since_widget.setCalendarPopup(True)
        self.since_widget.setDisplayFormat('yyyy-MM-dd HH:mm')
        since_layout = QHBoxLayout()
        since_layout.addWidget(QLabel('Since:'))
        since_layout.addWidget(self.since_widget)
        self.since_widget.dateTimeChanged.connect(search_results_model.on_since_time_changed)
        self.since_widget.setDateTime(QDateTime.fromSecsSinceEpoch(now - ONE_WEEK))

        self.until_widget = QDateTimeEdit()
        self.until_widget.setCalendarPopup(True)
        self.until_widget.setDisplayFormat('yyyy-MM-dd HH:mm')
        until_layout = QHBoxLayout()
        until_layout.addWidget(QLabel('Until:'))
        until_layout.addWidget(self.until_widget)
        self.until_widget.dateTimeChanged.connect(search_results_model.on_until_time_changed)
        self.until_widget.setDateTime(QDateTime.fromSecsSinceEpoch(now + ONE_WEEK))

        layout = QVBoxLayout()
        layout.addWidget(self.search_bar)
        layout.addLayout(since_layout)
        layout.addLayout(until_layout)
        self.setLayout(layout)
        self.search_bar.textChanged.connect(search_results_model.on_search_text_changed)


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
    def __init__(self, *args, search_results_model, **kwargs):
        super().__init__(*args, **kwargs)

        self.search_input_widget = SearchInputWidget(
            search_results_model=search_results_model)
        self.search_results_widget = SearchResultsWidget()
        self.search_results_widget.setModel(search_results_model)

        layout = QVBoxLayout()
        layout.addWidget(self.search_input_widget)
        layout.addWidget(self.search_results_widget)
        self.setLayout(layout)
