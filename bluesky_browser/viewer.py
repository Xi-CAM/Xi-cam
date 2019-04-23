from qtpy.QtWidgets import (
    QWidget,
    QTabWidget,
    )


class Container(QTabWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setTabsClosable(True)
        self.tabCloseRequested.connect(self.close_tab)
        self._runs = []

    def show_entries(self, entries):
        for entry in entries:
            uid = entry.metadata['start']['uid']
            if uid not in self._runs:
                # Add new Viewer tab.
                new_tab = Viewer(entry)
                self.addTab(new_tab, uid[:8])
                self._runs.append(uid)
        # Show the last entry in the list.
        index = self._runs.index(uid)
        self.setCurrentIndex(index)

    def close_tab(self, index):
        self._runs.pop(index)
        self.removeTab(index)


class Viewer(QWidget):
    def __init__(self, entry, *args, **kwargs):
        super().__init__(*args, **kwargs)
