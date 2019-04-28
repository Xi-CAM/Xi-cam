import enum
from functools import partial
import logging

from event_model import RunRouter
from qtpy.QtWidgets import (
    QAction,
    QActionGroup,
    QInputDialog,
    QTabWidget,
)

from .header_tree import HeaderTreeFactory
from .baseline import BaselineFactory
from .figures import FigureManager
from .utils import MoveableTabWidget


log = logging.getLogger('bluesky_browser')


class ViewerOuterTabs(MoveableTabWidget):
    def __init__(self, *args, menuBar, **kwargs):
        super().__init__(*args, **kwargs)
        self.setTabsClosable(True)
        self.tabCloseRequested.connect(self.close_tab)
        self._runs = []
        self._overplot = OverPlotState.off

        # TMP
        if menuBar is None:
            return

        overplot_group = QActionGroup(self)
        off = QAction('&Off')
        off.setStatusTip('Open a new viewer tab for each Run.')
        latest_live = QAction('&Latest Live Tab')
        latest_live.setStatusTip('Attempt to overplot on the most recent live Run.')
        fixed = QAction('&Fixed Tab...')
        fixed.setStatusTip('Attempt to overplot on a specific tab.')
        overplot_group.addAction(off)
        overplot_group.addAction(latest_live)
        overplot_group.addAction(fixed)
        for action in overplot_group.actions():
            action.setCheckable(True)
        overplot_group.setExclusive(True)
        off.setChecked(True)

        overplot_menu = menuBar().addMenu('&Over-plotting')
        overplot_menu.addActions(overplot_group.actions())

        off.triggered.connect(partial(self.set_overplot_state, OverPlotState.off))
        latest_live.triggered.connect(partial(self.set_overplot_state, OverPlotState.latest_live))

        def set_fixed_uid():
            self.set_overplot_state(OverPlotState.fixed)
            item, ok = QInputDialog.getItem(
                self, "Select Run", "Run", tuple(self._runs), 0, False)
            if not ok:
                # Abort and fallback to Off. Would be better to fall back to
                # previous state (which could be latest_live) but it's not
                # clear how to know what that state was.
                off.setChecked(True)
                return
            self.set_overplot_state(OverPlotState.fixed)
            print('fixed_uid', item)

        fixed.triggered.connect(set_fixed_uid)

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

    def set_overplot_state(self, state):
        log.debug('Overplot state is %s', state)
        self.overplot = state

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


class OverPlotState(enum.Enum):
    off = enum.auto()
    latest_live = enum.auto()
    fixed = enum.auto()
