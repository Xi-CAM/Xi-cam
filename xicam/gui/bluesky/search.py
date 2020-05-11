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

from qtpy.QtCore import Qt, Signal, QThread, QSettings
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
    QMenu,
    QApplication
)

from xicam.core import msg

from .utils import ConfigurableQObject
from .top_utils import load_config, Callable
from xicam.core import msg
from xicam.core import threads

MAX_SEARCH_RESULTS = 100  # TODO Use fetchMore instead of a hard limit.
log = logging.getLogger("bluesky_browser")
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
_validate = functools.partial(jsonschema.validate, types={"array": (list, tuple)})


def timeit(f):
    def wrap(*args):
        time1 = time.time()
        ret = f(*args)
        time2 = time.time()
        print("{:s} function took {:.3f} ms".format(f.__name__, (time2 - time1) * 1000.0))
        return ret

    return wrap


def default_search_result_row(entry):
    start = entry.metadata["start"]
    stop = entry.metadata["stop"]
    start_time = datetime.fromtimestamp(start["time"])
    if stop is None:
        str_duration = "-"
    else:
        duration = datetime.fromtimestamp(stop["time"]) - start_time
        str_duration = str(duration)
        str_duration = str_duration[: str_duration.index(".")]
    return {
        "Unique ID": start["uid"][:8],
        "Transient Scan ID": (start.get("scan_id", "-")),
        "Plan Name": start.get("plan_name", "-"),
        "Start Time": start_time.strftime("%Y-%m-%d %H:%M:%S"),
        "Duration": str_duration,
        "Exit Status": "-" if stop is None else stop["exit_status"],
    }

# TODO: implement threads with event-loops

class ReloadThread(QThread):
    def __init__(self, search_state):
        super(ReloadThread, self).__init__()
        self.search_state = search_state
        QApplication.instance().aboutToQuit.connect(self.quit)

    def run(self):
        while True:
            t0 = time.monotonic()
            # Never reload until the last reload finished being
            # displayed.
            self.search_state.show_results_event.wait()
            # Wait for RELOAD_INTERVAL to pass or until we are poked,
            # whichever happens first.
            self.search_state.reload_event.wait(max(0, RELOAD_INTERVAL - (time.monotonic() - t0)))
            self.search_state.reload_event.clear()
            # Reload the catalog to show any new results.
            self.search_state.reload()


class ProcessQueriesThread(QThread):
    def __init__(self, search_state):
        super(ProcessQueriesThread, self).__init__()
        self.search_state = search_state
        QApplication.instance().aboutToQuit.connect(self.quit)

    def run(self):
        while True:
            try:
                self.search_state.process_queries()
            except Exception as e:
                msg.logError(e)
                msg.showMessage("Unable to query: ", str(e))


class SearchState(ConfigurableQObject):
    """
    Encapsulates CatalogSelectionModel and SearchResultsModel. Executes search.
    """

    new_results_catalog = Signal([])
    sig_update_header = Signal()
    search_result_row = Callable(default_search_result_row, config=True)

    def __init__(self, catalog):
        self.last_results_thread = None
        self.update_config(load_config())
        self.selected_catalog = None
        self.root_catalog = self.flatten_remote_catalogs(catalog)
        self.enabled = False  # to block searches during initial configuration
        self.catalog_selection_model = CatalogSelectionModel()
        self.search_results_model = SearchResultsModel(self)
        self._subcatalogs = []  # to support lookup by item's positional index
        self.open_uids = set()  # to support quick lookup that a catalog is open
        self._results_catalog = None
        self._new_uids_queue = queue.Queue(maxsize=MAX_SEARCH_RESULTS)  # to pass reference of new catalogs across threads
        self.list_subcatalogs()
        self.set_selected_catalog(0)
        self.query_queue = queue.Queue()
        self.show_results_event = threading.Event()
        self.show_results_event.set()
        self.reload_event = threading.Event()

        super().__init__()

        self.new_results_catalog.connect(self.start_show_results)

        self.reload_thread = ReloadThread(self)
        self.reload_thread.start()
        self.process_queries_thread = ProcessQueriesThread(self)
        self.process_queries_thread.start()

    def start_show_results(self):
        self.last_results_thread = threads.QThreadFuture(self.show_results)
        self.last_results_thread.start()

    def flatten_remote_catalogs(self, catalog):
        from intake.catalog.base import Catalog

        cat_dict = {}

        for name in catalog:
            try:
                from intake.catalog.base import RemoteCatalog

                sub_cat = catalog[name]
                # @TODO remote catalogs are one level too high. This check is
                # pretty rough. Would rather check that a catalog's children
                # should be top-level.
                # This is making the terrible assumption that children
                # of a RemoteCatalog be treated as top-level. But until
                # we figure out how to tell that a catalog is a real catalog
                # with data, it's as good as we can get
                if isinstance(sub_cat(), RemoteCatalog):
                    for name in sub_cat:
                        cat_dict[name] = sub_cat[name]
                else:
                    cat_dict[name] = sub_cat
            except Exception as e:
                msg.logError(e)
                msg.showMessage("Unable to query top level catalogs: ", str(e))

        return Catalog.from_dict(cat_dict)

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
                _validate(entry.metadata["start"], event_model.schemas[event_model.DocumentNames.start])
            except jsonschema.ValidationError:
                log.exception("Invalid RunStart Document: %r", entry.metadata["start"])
                raise SkipRow("invalid document") from exc
            try:
                _validate(entry.metadata["stop"], event_model.schemas[event_model.DocumentNames.stop])
            except jsonschema.ValidationError:
                if entry.metadata["stop"] is None:
                    log.debug("Run %r has no RunStop document.", entry.metadata["start"]["uid"])
                else:
                    log.exception("Invalid RunStop Document: %r", entry.metadata["stop"])
                raise SkipRow("invalid document")
            log.exception("Run with uid %s raised error with search_result_row.", entry.metadata["start"]["uid"])
            raise SkipRow("error in search_result_row") from exc

    def __del__(self):
        if hasattr(self.reload_thread):
            self.reload_thread.terminate()

    def list_subcatalogs(self):
        self._subcatalogs.clear()
        self.catalog_selection_model.clear()
        if not self.root_catalog:
            return

        for name in self.root_catalog:
            self._subcatalogs.append(name)
            self.catalog_selection_model.appendRow(QStandardItem(str(name)))

    def set_selected_catalog(self, item):
        if len(self._subcatalogs) == 0:
            return
        name = self._subcatalogs[item]
        try:
            self.selected_catalog = self.root_catalog[name]()
            self.search()
        except Exception as e:
            log.error(e)
            msg.showMessage("Unable to contact catalog: ", str(e))

    def check_for_new_entries(self):
        # check for any new results and add them to the queue for later processing
        found_new = False
        for uid in itertools.islice(self._results_catalog, MAX_SEARCH_RESULTS):
            if uid in self.open_uids:
                continue
            self.open_uids.add(uid)
            self._new_uids_queue.put(uid)
            found_new = True
        return found_new

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
        log.debug("Submitting query %r", query)
        try:
            t0 = time.monotonic()
            msg.showMessage("Running Query")
            msg.showBusy()
            if not self.selected_catalog:
                return
            self._results_catalog = self.selected_catalog.search(query)
            found_new = self.check_for_new_entries()
            duration = time.monotonic() - t0
            log.debug("Query yielded %r results (%.3f s).", len(self._results_catalog), duration)
            if found_new and self.show_results_event.is_set():
                self.new_results_catalog.emit()
        except Exception as e:
            msg.logError(e)
            msg.showMessage("Problem running query")
        finally:
            msg.hideBusy()

    def search(self):
        self._new_uids_queue = queue.Queue(maxsize=MAX_SEARCH_RESULTS)
        if self.last_results_thread and not self.show_results_event.is_set():
            self.last_results_thread.requestInterruption()
            self.last_results_thread.wait()
        self.search_results_model.clear()
        self.search_results_model.selected_rows.clear()
        self.open_uids.clear()
        if not self.enabled:
            return
        query = {"time": {}}
        if self.search_results_model.since is not None:
            query["time"]["$gte"] = self.search_results_model.since
        if self.search_results_model.until is not None:
            query["time"]["$lt"] = self.search_results_model.until
        query.update(**self.search_results_model.custom_query)
        self.query_queue.put(query)

    @timeit
    def get_run_by_uid(self, uid):
        try:
            return self._results_catalog[uid]
        except Exception:
            raise SkipRow(f"error accessing documents for {uid}")

    def show_results(self):
        header_labels_set = False
        self.show_results_event.clear()
        t0 = time.monotonic()
        counter = 0

        try:
            msg.showBusy()
            while not self._new_uids_queue.empty():
                counter += 1
                row = []
                new_uid = self._new_uids_queue.get()
                try:
                    entry = self.get_run_by_uid(new_uid)
                    row_data = self.apply_search_result_row(entry)
                except SkipRow as e:
                    msg.showMessage(str(msg))
                    msg.logError(e)
                    continue
                if not header_labels_set:
                    # Set header labels just once.
                    threads.invoke_in_main_thread(self.search_results_model.setHorizontalHeaderLabels, list(row_data))
                    header_labels_set = True
                for value in row_data.values():
                    item = QStandardItem()
                    item.setData(value, Qt.DisplayRole)
                    item.setData(new_uid, Qt.UserRole)
                    row.append(item)
                if QThread.currentThread().isInterruptionRequested():
                    self.show_results_event.set()
                    msg.logMessage("Interrupt requested")
                    return
                threads.invoke_in_main_thread(self.search_results_model.appendRow, row)
            if counter:
                self.sig_update_header.emit()
                duration = time.monotonic() - t0
                msg.showMessage("Displayed {} new results {}.".format(counter, duration))
            self.show_results_event.set()
        except Exception as e:
            msg.showMessage("Error displaying runs")
            msg.logError(e)
        finally:
            msg.hideBusy()

    def reload(self):
        t0 = time.monotonic()
        if self._results_catalog is not None:
            try:
                self._results_catalog.reload()
                new_results = self.check_for_new_entries()
                duration = time.monotonic() - t0
                msg.logMessage("Reloaded search results {}.".format(duration))
                if new_results and self.show_results_event.is_set():
                    self.new_results_catalog.emit()
            except Exception as e:
                log.error(e)
                msg.showMessage("Unable to query top level catalogs: ", str(e))


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
    preview_entry = Signal(str, object)
    valid_custom_query = Signal([bool])

    def __init__(self, search_state, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.custom_query = {}
        self.search_state = search_state
        self.since = None
        self.until = None
        self.selected_rows = set()

    def emit_selected_result(self, selected, deselected):
        try:
            self.selected_rows |= set(index.row() for index in selected.indexes())
            self.selected_rows -= set(index.row() for index in deselected.indexes())
            entries = []
            for row in sorted(self.selected_rows):
                uid = self.data(self.index(row, 0), Qt.UserRole)
                entry = self.search_state._results_catalog[uid]
                entries.append(entry)
            self.selected_result.emit(entries)
        except Exception as e:
            msg.logError(e)
            msg.showMessage("Problem getting info about for selected row")

    def emit_open_entries(self, target, indexes):
        rows = set(index.row() for index in indexes)
        entries = []
        for row in rows:
            uid = self.data(self.index(row, 0), Qt.UserRole)
            entry = self.search_state._results_catalog[uid]
            entries.append(entry)
        self.open_entries.emit(target, entries)

    def emit_preview_entry(self, target, index):
        row = index.row()
        entries = []
        uid = self.data(self.index(row, 0), Qt.UserRole)
        entry = self.search_state._results_catalog[uid]
        entries.append(entry)
        self.preview_entry.emit(target, entry)

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
        search_bar_layout.addWidget(QLabel("Custom Query:"))
        search_bar_layout.addWidget(self.search_bar)
        mongo_query_help_button = QPushButton()
        mongo_query_help_button.setText("?")
        search_bar_layout.addWidget(mongo_query_help_button)
        mongo_query_help_button.clicked.connect(self.show_mongo_query_help)

        self.since_widget = QDateTimeEdit()
        self.since_widget.setCalendarPopup(True)
        self.since_widget.setDisplayFormat("yyyy-MM-dd HH:mm")
        since_layout = QHBoxLayout()
        since_layout.addWidget(QLabel("Since:"))
        since_layout.addWidget(self.since_widget)

        self.until_widget = QDateTimeEdit()
        self.until_widget.setCalendarPopup(True)
        self.until_widget.setDisplayFormat("yyyy-MM-dd HH:mm")
        until_layout = QHBoxLayout()
        until_layout.addWidget(QLabel("Until:"))
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
        msg.setInformativeText(
            """
Examples:

{'plan_name': 'scan'}
{'proposal': 1234},
{'$and': ['proposal': 1234, 'sample_name': 'Ni']}
"""
        )
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

    def hide_hidden_columns(self):
        hidden_columns = QSettings().value("catalog.columns.hidden") or set()
        header = self.horizontalHeader()
        current_column_names = [str(self.model().headerData(i, Qt.Horizontal)) for i in range(header.count())]
        current_hidden_names = hidden_columns.intersection(set(current_column_names))
        for name in current_hidden_names:
            header.setSectionHidden(current_column_names.index(name), True)


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

        header = self.search_results_widget.horizontalHeader()
        header.setContextMenuPolicy(Qt.CustomContextMenu)
        header.customContextMenuRequested.connect(self.header_menu)

    def _current_column_names(self, header):
        return [self._current_column_name(header, i) for i in range(header.count())]

    def _current_column_name(self, header, index):
        return str(header.model().headerData(index, Qt.Horizontal))

    def hide_column(self, header, logicalIndex):
        """
        Hide a column, adding the column from the list of hidden columns in QSettings
        """
        hidden_columns = QSettings().value("catalog.columns.hidden") or set()
        if len(hidden_columns) == header.count() - 1:
            msg.notifyMessage("Only one column is left to hide, cannot hide all of them.")
            return
        hidden_columns.add(self._current_column_name(header, logicalIndex))
        QSettings().setValue("catalog.columns.hidden", hidden_columns)
        header.setSectionHidden(logicalIndex, True)

    def unhide_column(self, header, logicalIndex):
        """
        Unhide a column, removing the column from the list of hidden columns in QSettings
        """
        hidden_columns = QSettings().value("catalog.columns.hidden") or set()
        column_name = self._current_column_name(header, logicalIndex)
        try:
            hidden_columns.remove(column_name)
        except KeyError as ex:
            raise (KeyError(f"Attempted to unhide non-hidden column name {column_name}."))
        QSettings().setValue("catalog.columns.hidden", hidden_columns)
        header.setSectionHidden(logicalIndex, False)

    def header_menu(self, position):
        """
        Creates a menu allowing users to show and hide columns
        """
        header = self.sender()  # type: QHeaderView
        index = header.logicalIndexAt(position)
        menu = QMenu("Options")
        action = menu.addAction("Hide Column")  # type: QAction
        column_name = str(header.model().headerData(index, Qt.Horizontal))
        action.triggered.connect(lambda: self.hide_column(header, index))
        show_columns_menu = menu.addMenu("Show Columns")

        for i in range(header.count()):
            if header.isSectionHidden(i):
                column_name = str(header.model().headerData(i, Qt.Horizontal))
                action = show_columns_menu.addAction(column_name)
                action.triggered.connect(functools.partial(self.unhide_column, header, i))
                # why does below work, but not: lambda: self.unhide_column(header, i)
                # action.triggered.connect(lambda triggered, logicalIndex=i: self.unhide_column(header, logicalIndex))

        menu.exec_(header.mapToGlobal(position))


class SkipRow(Exception):
    ...
