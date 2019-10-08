import argparse
import logging
import os
import pkg_resources
import sys
import time

from intake import Catalog
from qtpy.QtCore import QDateTime, Qt
from qtpy.QtWidgets import (
    QApplication,
    QWidget,
    QMainWindow,
    QHBoxLayout,
    QSplitter)

from .search import SearchWidget, SearchState
from .summary import SummaryWidget
from .viewer import Viewer
from ...zmq import ConsumerThread
from ... import __version__


log = logging.getLogger('bluesky_browser')


class CentralWidget(QWidget):
    """
    Encapsulates all widgets and models. Connect signals on __init__.
    """
    def __init__(self, *args,
                 catalog, menuBar,
                 zmq_address=None, **kwargs):
        super().__init__(*args, **kwargs)

        # Define models.
        search_state = SearchState(
            catalog=catalog)

        # Define widgets.
        self.search_widget = SearchWidget()
        self.summary_widget = SummaryWidget()

        left_pane = QSplitter(Qt.Vertical)
        left_pane.addWidget(self.search_widget)
        left_pane.addWidget(self.summary_widget)

        self.viewer = Viewer(menuBar=menuBar)

        layout = QHBoxLayout()
        splitter = QSplitter(Qt.Horizontal)
        layout.addWidget(splitter)
        splitter.addWidget(left_pane)
        splitter.addWidget(self.viewer)
        self.setLayout(layout)

        def show_double_clicked_entry(index):
            search_state.search_results_model.emit_open_entries(None, [index])

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
            search_state.search_results_model.emit_selected_result)
        self.search_widget.search_results_widget.doubleClicked.connect(
            show_double_clicked_entry)
        search_state.search_results_model.selected_result.connect(
            self.summary_widget.set_entries)
        search_state.search_results_model.open_entries.connect(
            self.viewer.show_entries)
        self.summary_widget.open.connect(self.viewer.show_entries)
        self.viewer.tab_titles.connect(self.summary_widget.cache_tab_titles)
        search_state.search_results_model.valid_custom_query.connect(
            self.search_widget.search_input_widget.mark_custom_query)
        search_state.enabled = True
        search_state.search()

        if zmq_address:

            def request_reload_after_delay(uid):
                DELAY = 2  # Wait for RunStart to be available in Catalog.
                time.sleep(DELAY)
                search_state.request_reload()

            self.consumer_thread = ConsumerThread(zmq_address=zmq_address)
            self.consumer_thread.documents.connect(self.viewer.consumer)
            self.consumer_thread.new_run_uid.connect(
                request_reload_after_delay)
            self.consumer_thread.start()


def main():
    parser = argparse.ArgumentParser(description='Prototype bluesky data browser',
                                     epilog=f'version {__version__}')
    parser.register('action', 'demo', _DemoAction)
    parser.register('action', 'generate_config', _GenerateConfigAction)
    parser.add_argument('catalog', type=str)
    parser.add_argument('-z', '--zmq-address', dest='zmq_address',
                        default=None, type=str,
                        help='0MQ remote dispatcher address (host:port)')
    parser.add_argument('--verbose', '-v', action='count')
    parser.add_argument('--demo', action='demo',
                        default=argparse.SUPPRESS,
                        help="Launch the app with example data.")
    parser.add_argument('--generate-config', action='generate_config',
                        default=argparse.SUPPRESS,
                        help="Generate a configuration file.")
    args = parser.parse_args()
    if args.verbose:
        handler = logging.StreamHandler()
        handler.setLevel('DEBUG')
        log.addHandler(handler)
        log.setLevel('DEBUG')
    app = build_app(args.catalog, zmq_address=args.zmq_address)
    sys.exit(app.exec_())


def build_app(catalog_uri, zmq_address=None):
    catalog = Catalog(catalog_uri)

    app = QApplication([b'Bluesky Browser'])
    app.main_window = QMainWindow()
    central_widget = CentralWidget(
        catalog=catalog,
        zmq_address=zmq_address,
        menuBar=app.main_window.menuBar)
    app.main_window.setCentralWidget(central_widget)
    app.main_window.show()
    return app


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
        handler = logging.StreamHandler()
        handler.setLevel('DEBUG')
        log.addHandler(handler)
        log.setLevel('DEBUG')

        from ...demo import generate_example_catalog, stream_example_data
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as directory:
            catalog_filepath = generate_example_catalog(directory)
            zmq_address, proxy_process, publisher_process = stream_example_data(directory)
            app = build_app(catalog_filepath, zmq_address)
            app.main_window.centralWidget().viewer.off.setChecked(True)
            try:
                ret = app.exec_()
            finally:
                proxy_process.terminate()
                publisher_process.terminate()
                sys.exit(ret)
                parser.exit()


class _GenerateConfigAction(argparse.Action):
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
        filepath = pkg_resources.resource_filename('bluesky_browser', 'example_config.py')
        with open(filepath) as example_config:
            if os.path.exists('bluesky_browser_config.py'):
                overwrite = input("Overwite bluesky_browser_config.py? (y/n) ")
                if overwrite != 'y':
                    print("Quitting without writing.")
                    parser.exit()
                    return
            with open('bluesky_browser_config.py', 'w') as file:
                print("Writing default configuration file to bluesky_browser_config.py...")
                file.write(example_config.read())
        parser.exit()


if __name__ == '__main__':
    main()
