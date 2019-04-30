from event_model import unpack_event_page
from qtpy.QtGui import QStandardItemModel, QStandardItem
from qtpy.QtWidgets import QTableView, QWidget, QVBoxLayout


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


class BaselineFactory:
    def __init__(self, add_tab):
        container = QWidget()
        self.layout = QVBoxLayout()
        container.setLayout(self.layout)
        add_tab(container, 'Baseline')

    def __call__(self, name, start_doc):
        def subfactory(name, descriptor_doc):
            if descriptor_doc.get('name') == 'baseline':
                baseline_widget = BaselineWidget()
                baseline_model = BaselineModel()
                baseline_widget.setModel(baseline_model)
                self.layout.addWidget(baseline_widget)
                return [baseline_model]
            else:
                return []
        return [], [subfactory]
