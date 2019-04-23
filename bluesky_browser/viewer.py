from event_model import RunRouter, unpack_event_page
from qtpy.QtGui import QStandardItemModel, QStandardItem
from qtpy.QtWidgets import (
    QTableView,
    QTabWidget,
    )

from .header_tree import HeaderTreeWidget


class Container(QTabWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setTabsClosable(True)
        self.tabCloseRequested.connect(self.close_tab)
        self._runs = []

    def show_entries(self, entries):
        for entry in entries:
            run_catalog = entry()
            uid = run_catalog.metadata['start']['uid']
            if uid not in self._runs:
                # Add new Viewer tab.
                viewer = Viewer()
                for name, doc in run_catalog.read_canonical():
                    viewer.run_router(name, doc)
                self.addTab(viewer, uid[:8])
                self._runs.append(uid)
        if entries:
            # Show the last entry in the list.
            index = self._runs.index(uid)
            self.setCurrentIndex(index)

    def close_tab(self, index):
        self._runs.pop(index)
        self.removeTab(index)


class Viewer(QTabWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.run_router = RunRouter([self.factory])

    def factory(self, name, start_doc):
        header_tree_widget = HeaderTreeWidget()
        header_tree_widget('start', start_doc)
        self.addTab(header_tree_widget, 'Header')

        def subfactory(name, descriptor_doc):
            if descriptor_doc.get('name') == 'baseline':
                baseline_widget = BaselineWidget()
                baseline_model = BaselineModel()
                baseline_widget.setModel(baseline_model)
                self.addTab(baseline_widget, 'Baseline')
                return [baseline_model]
            else:
                return []
        return [], [subfactory, header_tree_widget]


class BaselineModel(QStandardItemModel):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setHorizontalHeaderLabels(['Before', 'After'])

    def __call__(self, name, doc):
        if name == 'event_page':
            for event in unpack_event_page(doc):
                self.__call__('event', event)
        elif name == 'event':
            column = doc['seq_num'] - 1
            for row, val in enumerate(val for _, val in sorted(doc['data'].items())):
                self.setItem(row, column, QStandardItem(str(val)))
            self.setVerticalHeaderLabels(doc['data'].keys())


class BaselineWidget(QTableView):
    ...
