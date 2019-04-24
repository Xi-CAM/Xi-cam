from qtpy.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
    )


class SummaryWidget(QWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.uid_label = QLabel()
        self.copy_uid_button = QPushButton('Copy UID to Clipboard')
        self.copy_uid_button.clicked.connect(self._copy_uid)
        self.streams = QLabel()

        uid_layout = QHBoxLayout()
        uid_layout.addWidget(self.uid_label)
        uid_layout.addWidget(self.copy_uid_button)
        layout = QVBoxLayout()
        layout.addLayout(uid_layout)
        layout.addWidget(self.streams)
        self.setLayout(layout)

    # @QtCore.pyqtSlot()
    def _copy_uid(self):
        QApplication.clipboard().setText(self.uid)

    def set_entries(self, entries):
        if len(entries) != 1:
            self.uid_label.setText('')
            self.streams.setText('')
            self.copy_uid_button.hide()
            return
        entry, = entries
        self.uid = entry.metadata['start']['uid']
        self.uid_label.setText(self.uid[:8])
        self.copy_uid_button.show()
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
