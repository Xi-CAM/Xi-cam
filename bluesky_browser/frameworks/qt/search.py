"""
Experimental Qt-based data browser for bluesky
"""
import ast
from datetime import datetime
import event_model
import functools
import itertools
import jsonschema
import logging
import queue
import threading
import time

from qtpy.QtCore import Qt, Signal, QThread
from qtpy.QtGui import QStandardItemModel, QStandardItem
from qtpy.QtWidgets import (
    QAbstractItemView,
    QPushButton,
    QComboBox,
    QDateTimeEdit,
    QHeaderView,
    QHBoxLayout,
    QMessageBox,
    QLabel,
    QLineEdit,
    QVBoxLayout,
    QWidget,
    QTableView,
    )
from .utils import ConfigurableQObject
from ...utils import load_config, Callable


MAX_SEARCH_RESULTS = 100  # TODO Use fetchMore instead of a hard limit.
log = logging.getLogger('bluesky_browser')
BAD_TEXT_INPUT = """
QLineEdit {
    background-color: rgb(255, 100, 100);
}
"""
GOOD_TEXT_INPUT = """
QLineEdit {
    background-color: rgb(255, 255, 255);
}
"""
RELOAD_INTERVAL = 11
_validate = functools.partial(jsonschema.validate, types={'array': (list, tuple)})


def default_search_result_row(entry):
    metadata = entry.describe()['metadata']
    start = metadata['start']
    stop = metadata['stop']
    start_time = datetime.fromtimestamp(start['time'])
    if stop is None:
        str_duration = '-'
    else:
        duration = datetime.fromtimestamp(stop['time']) - start_time
        str_duration = str(duration)
        str_duration = str_duration[:str_duration.index('.')]
    return {'Unique ID': start['uid'][:8],
            'Transient Scan ID': (start.get('scan_id', '-')),
            'Plan Name': start.get('plan_name', '-'),
            'Start Time': start_time.strftime('%Y-%m-%d %H:%M:%S'),
            'Duration': str_duration,
            'Exit Status': '-' if stop is None else stop['exit_status']}


class SearchState(ConfigurableQObject):
    """
    Encapsulates CatalogSelectionModel and SearchResultsModel. Executes search.
    """
    new_results_catalog = Signal([])
    new_results_catalog = Signal([])
    search_result_row = Callable(default_search_result_row, config=True)

    def __init__(self, catalog):
        self.update_config(load_config())
        self.catalog = catalog
        self.enabled = False  # to block searches during initial configuration
        self.catalog_selection_model = CatalogSelectionModel()
        self.search_results_model = SearchResultsModel(self)
        self._subcatalogs = []  # to support lookup by item's positional index
        self._results = []  # to support lookup by item's positional index
        self._results_catalog = None
        self._new_entries = queue.Queue(maxsize=MAX_SEARCH_RESULTS)
        self.list_subcatalogs()
        self.set_selected_catalog(0)
        self.query_queue = queue.Queue()
        self.show_results_event = threading.Event()
        self.reload_event = threading.Event()

        search_state = self

        super().__init__()

        self.new_results_catalog.connect(self.show_results)

        class ReloadThread(QThread):
            def run(self):
                while True:
                    t0 = time.monotonic()
                    # Never reload until the last reload finished being
                    # displayed.
                    search_state.show_results_event.wait()
                    # Wait for RELOAD_INTERVAL to pass or until we are poked,
                    # whichever happens first.
                    search_state.reload_event.wait(
                        max(0, RELOAD_INTERVAL - (time.monotonic() - t0)))
                    search_state.reload_event.clear()
                    # Reload the catalog to show any new results.
                    search_state.reload()

        self.reload_thread = ReloadThread()
        self.reload_thread.start()

        class ProcessQueriesThread(QThread):
            def run(self):
                while True:
                    search_state.process_queries()

        self.process_queries_thread = ProcessQueriesThread()
        self.process_queries_thread.start()

    def request_reload(self):
        self._results_catalog.force_reload()
        self.reload_event.set()

    def apply_search_result_row(self, entry):
        try:
            return self.search_result_row(entry)
        except Exception as exc:
            # Either the documents in entry are not valid or the definition of
            # search_result_row (which will be user-configurable) has failed to
            # account for some possiblity. Figure out which situation this is.
            try:
                _validate(entry.metadata['start'],
                          event_model.schemas[event_model.DocumentNames.start])
            except jsonschema.ValidationError:
                log.exception("Invalid RunStart Document: %r",
                              entry.metadata['start'])
                raise SkipRow("invalid document") from exc
            try:
                _validate(entry.metadata['stop'],
                          event_model.schemas[event_model.DocumentNames.stop])
            except jsonschema.ValidationError:
                if entry.metadata['stop'] is None:
                    log.debug("Run %r has no RunStop document.",
                              entry.metadata['start']['uid'])
                else:
                    log.exception("Invalid RunStop Document: %r",
                                  entry.metadata['stop'])
                raise SkipRow("invalid document")
            log.exception("Run with uid %s raised error with search_result_row.",
                          entry.metadata['start']['uid'])
            raise SkipRow("error in search_result_row") from exc

    def __del__(self):
        if hasattr(self.reload_thread):
            self.reload_thread.terminate()

    def list_subcatalogs(self):
        self._subcatalogs.clear()
        self.catalog_selection_model.clear()
        for name in self.catalog:
            self._subcatalogs.append(name)
            self.catalog_selection_model.appendRow(QStandardItem(str(name)))

    def set_selected_catalog(self, item):
        name = self._subcatalogs[item]
        self.selected_catalog = self.catalog[name]()
        self.search()

    def check_for_new_entries(self):
        # check for any new results and add them to the queue for later processing
        for uid, entry in itertools.islice(self._results_catalog.items(), MAX_SEARCH_RESULTS):
            if uid in self._results:
                continue
            self._results.append(uid)
            self._new_entries.put(entry)

    def process_queries(self):
        # If there is a backlog, process only the newer query.
        block = True
        while True:
            try:
                query = self.query_queue.get_nowait()
                block = False
            except queue.Empty:
                if block:
                    query = self.query_queue.get()
                break
        log.debug('Submitting query %r', query)
        t0 = time.monotonic()
        self._results_catalog = self.selected_catalog.search(query)
        self.check_for_new_entries()
        duration = time.monotonic() - t0
        log.debug('Query yielded %r results (%.3f s).',
                  len(self._results_catalog), duration)
        self.new_results_catalog.emit()

    def search(self):
        self.search_results_model.clear()
        self.search_results_model.selected_rows.clear()
        self._results.clear()
        if not self.enabled:
            return
        query = {'time': {}}
        if self.search_results_model.since is not None:
            query['time']['$gte'] = self.search_results_model.since
        if self.search_results_model.until is not None:
            query['time']['$lt'] = self.search_results_model.until
        query.update(**self.search_results_model.custom_query)
        self.query_queue.put(query)

    def show_results(self):
        header_labels_set = False
        self.show_results_event.clear()
        t0 = time.monotonic()
        counter = 0

        while not self._new_entries.empty():
            counter += 1
            entry = self._new_entries.get()
            row = []
            try:
                row_data = self.apply_search_result_row(entry)
            except SkipRow:
                continue
            if not header_labels_set:
                # Set header labels just once.
                self.search_results_model.setHorizontalHeaderLabels(list(row_data))
                header_labels_set = True
            for value in row_data.values():
                item = QStandardItem()
                item.setData(value, Qt.DisplayRole)
                row.append(item)
            self.search_results_model.appendRow(row)
        if counter:
            duration = time.monotonic() - t0
            log.debug("Displayed %d new results (%.3f s).", counter, duration)
        self.show_results_event.set()

    def reload(self):
        t0 = time.monotonic()
        if self._results_catalog is not None:
            self._results_catalog.reload()
            self.check_for_new_entries()
            duration = time.monotonic() - t0
            log.debug("Reloaded search results (%.3f s).", duration)
            self.new_results_catalog.emit()


class CatalogSelectionModel(QStandardItemModel):
    """
    List the subcatalogs in the root Catalog.
    """
    ...


class SearchResultsModel(QStandardItemModel):
    """
    Perform searches on a Catalog and model the results.
    """
    selected_result = Signal([list])
    open_entries = Signal([str, list])
    valid_custom_query = Signal([bool])

    def __init__(self, search_state, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.custom_query = {}
        self.search_state = search_state
        self.since = None
        self.until = None
        self.selected_rows = set()

    def emit_selected_result(self, selected, deselected):
        self.selected_rows |= set(index.row() for index in selected.indexes())
        self.selected_rows -= set(index.row() for index in deselected.indexes())
        entries = []
        for row in sorted(self.selected_rows):
            uid = self.search_state._results[row]
            entry = self.search_state._results_catalog[uid]
            entries.append(entry)
        self.selected_result.emit(entries)

    def emit_open_entries(self, target, indexes):
        rows = set(index.row() for index in indexes)
        entries = []
        for row in rows:
            uid = self.search_state._results[row]
            entry = self.search_state._results_catalog[uid]
            entries.append(entry)
        self.open_entries.emit(target, entries)

    def on_search_text_changed(self, text):
        try:
            self.custom_query = dict(ast.literal_eval(text)) if text else {}
        except Exception:
            self.valid_custom_query.emit(False)
        else:
            self.valid_custom_query.emit(True)
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

    def mark_custom_query(self, valid):
        "Indicate whether the current text is a parsable query."
        if valid:
            stylesheet = GOOD_TEXT_INPUT
        else:
            stylesheet = BAD_TEXT_INPUT
        self.search_bar.setStyleSheet(stylesheet)

    def show_mongo_query_help(self):
        "Launch a Message Box with instructions for custom queries."
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
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.setSortingEnabled(True)
        self.setSelectionBehavior(QTableView.SelectRows)
        self.setShowGrid(False)
        self.verticalHeader().setVisible(False)
        self.horizontalHeader().setDefaultAlignment(Qt.AlignHCenter)
        self.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.setAlternatingRowColors(True)


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


class SkipRow(Exception):
    ...
