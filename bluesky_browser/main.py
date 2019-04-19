import sys
import time

from qtpy.QtCore import QDateTime, Qt
from qtpy.QtWidgets import (
    QApplication,
    QWidget,
    QMainWindow,
    QHBoxLayout,
    QVBoxLayout)
from .search import SearchWidget, SearchState
from .summary import SummaryWidget


class CentralWidget(QWidget):
    """
    Encapsulates all widgets
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.search_widget = SearchWidget()
        self.summary_widget = SummaryWidget()

        left_pane = QVBoxLayout()
        left_pane.addWidget(self.search_widget)
        # left_pane.addWidget(self.summary_widget)

        layout = QHBoxLayout()
        layout.addLayout(left_pane)
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
        central_widget.search_widget.search_input_widget.until_widget.dateTimeChanged.connect(
            search_state.search_results_model.on_until_time_changed)
        central_widget.search_widget.search_input_widget.until_widget.setDateTime(
            QDateTime.fromSecsSinceEpoch(now + ONE_WEEK))
        central_widget.search_widget.search_input_widget.since_widget.dateTimeChanged.connect(
            search_state.search_results_model.on_since_time_changed)
        central_widget.search_widget.search_input_widget.since_widget.setDateTime(
            QDateTime.fromSecsSinceEpoch(now - ONE_WEEK))
        central_widget.search_widget.search_results_widget.selectionModel().selectionChanged.connect(print)


def main():
    """Start the application."""
    import logging
    log = logging.getLogger('bluesky_browser')
    handler = logging.StreamHandler()
    handler.setLevel('DEBUG')
    log.addHandler(handler)
    log.setLevel('DEBUG')

    from intake import Catalog
    catalog = Catalog('intake://localhost:5000')['xyz']()

    def search_result_row(entry):
        return {'Unique ID': entry.metadata['start']['uid'][:8],
                'Time': str(entry.metadata['start']['time']),
                'Num. of Events': str(sum(entry.metadata['stop'].get('num_events', {}).values()))}

    app = Application([b'Bluesky Browser'],
                      catalog=catalog,
                      search_result_row=search_result_row)

    app.main_window.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
