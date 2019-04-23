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
        self.streams.setText('\n'.join(list(entry())))
