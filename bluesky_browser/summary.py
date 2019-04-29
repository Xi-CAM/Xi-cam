from qtpy.QtCore import Signal
from qtpy.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
    )


class SummaryWidget(QWidget):
    open = Signal([list])

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.uid_label = QLabel()
        self.open_button = QPushButton('Open in Viewer')
        self.open_button.clicked.connect(self._open)
        self.copy_uid_button = QPushButton('Copy UID to Clipboard')
        self.copy_uid_button.hide()
        self.copy_uid_button.clicked.connect(self._copy_uid)
        self.streams = QLabel()
        self.entries = []

        uid_layout = QHBoxLayout()
        uid_layout.addWidget(self.uid_label)
        uid_layout.addWidget(self.copy_uid_button)
        layout = QVBoxLayout()
        layout.addWidget(self.open_button)
        layout.addLayout(uid_layout)
        layout.addWidget(self.streams)
        self.setLayout(layout)

    # @QtCore.pyqtSlot()
    def _copy_uid(self):
        QApplication.clipboard().setText(self.uid)

    def _open(self):
        self.open.emit(self.entries)

    def set_entries(self, entries):
        self.entries.clear()
        self.entries.extend(entries)
        if not entries:
            self.uid_label.setText('')
            self.streams.setText('')
            self.copy_uid_button.hide()
            self.open_button.hide()
        elif len(entries) == 1:
            entry, = entries
            self.uid = entry.metadata['start']['uid']
            self.uid_label.setText(self.uid[:8])
            self.copy_uid_button.show()
            self.open_button.show()
            num_events = entry.metadata.get('stop', {}).get('num_events')
            if num_events:
                self.streams.setText(
                    'Streams:\n' + ('\n'.join(f'{k} ({v} Events)' for k, v in num_events.items())))
            else:
                # Either the RunStop document has not been emitted yet or was never
                # emitted due to critical failure or this is an old document stream
                # from before 'num_events' was added to the schema. Get the list of
                # stream names another way, and omit the Event count.
                self.streams.setText('Streams:\n' + ('\n'.join(list(entry()))))
        else:
            self.uid_label.setText('(Multiple Selected)')
            self.streams.setText('')
            self.copy_uid_button.hide()
            self.open_button.show()
