import sys

from qtpy.QtWidgets import QApplication, QWidget, QMainWindow, QHBoxLayout
from .search import SearchWidget, SearchResultsModel


class CentralWidget(QWidget):
    def __init__(self, *args, search_results_model, **kwargs):
        super().__init__(*args, **kwargs)

        search_widget = SearchWidget(search_results_model=search_results_model)

        layout = QHBoxLayout()
        layout.addWidget(search_widget)
        self.setLayout(layout)


class Application(QApplication):
    ...


def main():
    app = Application([b'Bluesky Browser'])

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

    search_results_model = SearchResultsModel(
        catalog=catalog,
        search_result_row=search_result_row)
    central_widget = CentralWidget(
        search_results_model=search_results_model)

    main_window = QMainWindow()
    main_window.setCentralWidget(central_widget)
    main_window.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
