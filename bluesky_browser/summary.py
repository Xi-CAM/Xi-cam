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


class SummaryWidget(QWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.uid = QLabel() 
        self.streams = QLabel()

        layout = QVBoxLayout()
        layout.addWidget(self.uid)
        layout.addWidget(self.streams)
        self.setLayout(layout)

    def set_entries(self, entries):
        if len(entries) != 1:
            self.uid.setText('')
            self.streams.setText('')
            return
        entry, = entries
        self.uid.setText(entry.metadata['start']['uid'])
        self.streams.setText('\n'.join(list(entry())))
