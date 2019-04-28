import argparse
from datetime import datetime
from functools import partial
import sys
import time
from . import __version__

from qtpy.QtCore import QDateTime
from qtpy.QtWidgets import (
    QAction,
    QActionGroup,
    QApplication,
    QInputDialog,
    QWidget,
    QMainWindow,
    QHBoxLayout,
    QVBoxLayout)
from .search import SearchWidget, SearchState
from .summary import SummaryWidget
from .viewer import ViewerOuterTabs
from .utils import MoveableTabContainer, OverPlotState


class CentralWidget(QWidget):
    """
    Encapsulates all widgets and models. Connect signals on __init__.
    """
    def __init__(self, *args, catalog, search_result_row, **kwargs):
        super().__init__(*args, **kwargs)

        # Define models.
        search_state = SearchState(
            catalog=catalog,
            search_result_row=search_result_row)

        # Define widgets.
        self.search_widget = SearchWidget()
        self.summary_widget = SummaryWidget()

        left_pane = QVBoxLayout()
        left_pane.addWidget(self.search_widget)
        left_pane.addWidget(self.summary_widget)

        right_pane = QVBoxLayout()
        container = MoveableTabContainer()
        self.upper_viewer = ViewerOuterTabs(container)
        self.lower_viewer = ViewerOuterTabs(container)

        layout = QVBoxLayout()
        layout.addWidget(self.upper_viewer)
        layout.addWidget(self.lower_viewer)
        container.setLayout(layout)
        right_pane.addWidget(container)

        layout = QHBoxLayout()
        layout.addLayout(left_pane)
        layout.addLayout(right_pane)
        self.setLayout(layout)

        # Set models, connect signals, and set initial values.
        now = time.time()
        ONE_WEEK = 60 * 60 * 24 * 7
        self.search_widget.search_results_widget.setModel(
            search_state.search_results_model)
        self.search_widget.search_input_widget.search_bar.textChanged.connect(
            search_state.search_results_model.on_search_text_changed)
        self.search_widget.catalog_selection_widget.catalog_list.setModel(
            search_state.catalog_selection_model)
        self.search_widget.search_input_widget.until_widget.dateTimeChanged.connect(
            search_state.search_results_model.on_until_time_changed)
        self.search_widget.search_input_widget.until_widget.setDateTime(
            QDateTime.fromSecsSinceEpoch(now + ONE_WEEK))
        self.search_widget.search_input_widget.since_widget.dateTimeChanged.connect(
            search_state.search_results_model.on_since_time_changed)
        self.search_widget.search_input_widget.since_widget.setDateTime(
            QDateTime.fromSecsSinceEpoch(now - ONE_WEEK))
        self.search_widget.catalog_selection_widget.catalog_list.currentIndexChanged.connect(
            search_state.set_selected_catalog)
        self.search_widget.search_results_widget.selectionModel().selectionChanged.connect(
            search_state.search_results_model.emit_selected_result_signal)
        search_state.search_results_model.selected_result_signal.connect(
            self.summary_widget.set_entries)
        search_state.search_results_model.selected_result_signal.connect(
            self.upper_viewer.show_entries)
        search_state.search_results_model.valid_custom_query.connect(
            self.search_widget.search_input_widget.mark_custom_query)


def main():
    parser = argparse.ArgumentParser(description='Prototype bluesky data browser',
                                     epilog=f'version {__version__}')
    parser.register('action', 'demo', _DemoAction)
    parser.add_argument('catalog', type=str)
    parser.add_argument('--demo', action='demo',
                        default=argparse.SUPPRESS,
                        help="Launch the app with example data.")
    args = parser.parse_args()
    run(args.catalog_uri)


class MainWindow(QMainWindow):
    def __init__(self, set_overplot_state, list_open_runs, *args, **kwargs):
        super().__init__(*args, **kwargs)

        overplot_group = QActionGroup(self)
        off = QAction('&Off')
        off.setStatusTip('Open a new viewer tab for each Run.')
        latest_live = QAction('&Latest Live Tab')
        latest_live.setStatusTip('Attempt to overplot on the most recent live Run.')
        fixed = QAction('&Fixed Tab...')
        fixed.setStatusTip('Attempt to overplot on a specific tab.')
        overplot_group.addAction(off)
        overplot_group.addAction(latest_live)
        overplot_group.addAction(fixed)
        for action in overplot_group.actions():
            action.setCheckable(True)
        overplot_group.setExclusive(True)
        off.setChecked(True)

        menubar = self.menuBar()
        overplot_menu = menubar.addMenu('&Over-plotting')
        overplot_menu.addActions(overplot_group.actions())



        off.triggered.connect(partial(set_overplot_state, OverPlotState.off))
        latest_live.triggered.connect(partial(set_overplot_state, OverPlotState.latest_live))
        
        def set_fixed_uid():
            set_overplot_state(OverPlotState.fixed)
            items = list_open_runs()
            print(items)
            item, ok = QInputDialog.getItem(self, "Select Run", "Run", items, 0, False)
            if not ok:
                # Abort and fallback to Off. Would be better to fall back to
                # previous state (which could be latest_live) but it's not
                # clear how to know what that state was.
                off.setChecked(True)
                return
            set_overplot_state(OverPlotState.fixed)
            print('fixed_uid', item)

        fixed.triggered.connect(set_fixed_uid)


def run(catalog_uri):
    import logging
    log = logging.getLogger('bluesky_browser')
    handler = logging.StreamHandler()
    handler.setLevel('DEBUG')
    log.addHandler(handler)
    log.setLevel('DEBUG')

    from intake import Catalog
    catalog = Catalog(catalog_uri)

    # TODO Make search_result_row configurable.

    def search_result_row(entry):
        start = entry.metadata['start']
        stop = entry.metadata['stop']
        return {'Unique ID': start['uid'][:8],
                'Transient Scan ID': str(start.get('scan_id', '-')),
                'Plan Name': start.get('plan_name', '-'),
                'Time': datetime.fromtimestamp(start['time']).strftime('%Y-%m-%d %H:%M:%S'),
                'Exit Status': stop['exit_status']}

    app = QApplication([b'Bluesky Browser'])
    central_widget = CentralWidget(
        catalog=catalog,
        search_result_row=search_result_row)
    app.main_window = MainWindow(
        central_widget.upper_viewer.set_overplot_state,
        central_widget.upper_viewer.list_open_runs)
    app.main_window.setCentralWidget(central_widget)
    app.main_window.show()
    sys.exit(app.exec_())


class _DemoAction(argparse.Action):
    """
    A special action that generates example data and launches the app.

    This overrides the parser's required arguments the same way that --help
    does, so that the user does not have to pass in a catalog in this case.
    """
    def __init__(self,
                 option_strings,
                 dest=argparse.SUPPRESS,
                 default=argparse.SUPPRESS,
                 help=None):
        super().__init__(
            option_strings=option_strings,
            dest=dest,
            default=default,
            nargs=0,
            help=help)

    def __call__(self, parser, namespace, values, option_string=None):
        from .demo import generate_example_data
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as directory:
            catalog_filepath = generate_example_data(directory)
            run(catalog_filepath)
            parser.exit()


if __name__ == '__main__':
    main()
