import argparse
from datetime import datetime
import sys
import time
from . import __version__

from qtpy.QtCore import QDateTime
from qtpy.QtWidgets import (
    QApplication,
    QWidget,
    QMainWindow,
    QHBoxLayout,
    QVBoxLayout)
from .search import SearchWidget, SearchState
from .summary import SummaryWidget
from .viewer import Container


class CentralWidget(QWidget):
    """
    Encapsulates all widgets
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.search_widget = SearchWidget()
        self.summary_widget = SummaryWidget()
        self.container = Container()

        left_pane = QVBoxLayout()
        left_pane.addWidget(self.search_widget)
        left_pane.addWidget(self.summary_widget)

        right_pane = QVBoxLayout()
        right_pane.addWidget(self.container)

        layout = QHBoxLayout()
        layout.addLayout(left_pane)
        layout.addLayout(right_pane)
        self.setLayout(layout)


class Application(QApplication):
    """
    Encapsulates CentralWidget and all models. Connects signals on __init__.
    """
    def __init__(self, *args, catalog, search_result_row, **kwargs):
        super().__init__(*args, **kwargs)

        # Define models.
        search_state = SearchState(
            catalog=catalog,
            search_result_row=search_result_row)

        # Set up central widget.
        self.main_window = QMainWindow()
        central_widget = CentralWidget()
        self.main_window.setCentralWidget(central_widget)

        # Set models, connect signals, and set initial values.
        now = time.time()
        ONE_WEEK = 60 * 60 * 24 * 7
        central_widget.search_widget.search_results_widget.setModel(
            search_state.search_results_model)
        central_widget.search_widget.search_input_widget.search_bar.textChanged.connect(
            search_state.search_results_model.on_search_text_changed)
        central_widget.search_widget.catalog_selection_widget.catalog_list.setModel(
            search_state.catalog_selection_model)
        central_widget.search_widget.search_input_widget.until_widget.dateTimeChanged.connect(
            search_state.search_results_model.on_until_time_changed)
        central_widget.search_widget.search_input_widget.until_widget.setDateTime(
            QDateTime.fromSecsSinceEpoch(now + ONE_WEEK))
        central_widget.search_widget.search_input_widget.since_widget.dateTimeChanged.connect(
            search_state.search_results_model.on_since_time_changed)
        central_widget.search_widget.search_input_widget.since_widget.setDateTime(
            QDateTime.fromSecsSinceEpoch(now - ONE_WEEK))
        central_widget.search_widget.catalog_selection_widget.catalog_list.currentIndexChanged.connect(
            search_state.set_selected_catalog)
        central_widget.search_widget.search_results_widget.selectionModel().selectionChanged.connect(
            search_state.search_results_model.emit_selected_result_signal)
        search_state.search_results_model.selected_result_signal.connect(central_widget.summary_widget.set_entries)
        search_state.search_results_model.selected_result_signal.connect(central_widget.container.show_entries)
        search_state.search_results_model.valid_custom_query.connect(central_widget.search_widget.search_input_widget.mark_custom_query)


def run(catalog_uri):
    """
    Start the application with some defaults, until we get config sorted out.
    """
    import logging
    log = logging.getLogger('bluesky_browser')
    handler = logging.StreamHandler()
    handler.setLevel('DEBUG')
    log.addHandler(handler)
    log.setLevel('DEBUG')

    from intake import Catalog
    catalog = Catalog(catalog_uri)

    def search_result_row(entry):
        start = entry.metadata['start']
        stop = entry.metadata['stop']
        return {'Unique ID': start['uid'][:8],
                'Transient Scan ID': str(start.get('scan_id', '-')),
                'Plan Name': start.get('plan_name', '-'),
                'Time': datetime.fromtimestamp(start['time']).strftime('%Y-%m-%d %H:%M:%S'),
                'Exit Status': stop['exit_status']}

    app = Application([b'Bluesky Browser'],
                      catalog=catalog,
                      search_result_row=search_result_row)

    app.main_window.show()
    sys.exit(app.exec_())


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
