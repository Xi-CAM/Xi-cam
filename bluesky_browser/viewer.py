from event_model import RunRouter
from qtpy.QtWidgets import QTabWidget

from .header_tree import HeaderTreeFactory
from .baseline import BaselineFactory
from .figures import FigureManager
from .utils import MoveableTabWidget, MoveableTabContainer


class ViewerOuterTabs(MoveableTabWidget):
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
                viewer = ViewerInnerTabs()
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


class ViewerInnerTabs(QTabWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.run_router = RunRouter([
            BaselineFactory(self.addTab),
            HeaderTreeFactory(self.addTab),
            FigureManager(self.addTab),
            ])
