import collections
import enum
from functools import partial
import logging

from event_model import RunRouter
from qtpy.QtWidgets import (
    QAction,
    QActionGroup,
    QInputDialog,
    QTabWidget,
    QVBoxLayout,
)

from .header_tree import HeaderTreeFactory
from .baseline import BaselineFactory
from .figures import FigureManager
from .utils import MoveableTabWidget, MoveableTabContainer


log = logging.getLogger('bluesky_browser')


class Viewer(MoveableTabContainer):
    """
    Contains multiple TabbedViewingAreas
    """
    def __init__(self, *args, menuBar, **kwargs):
        super().__init__(*args, **kwargs)
        self._run_to_tabs = collections.defaultdict(list)
        self._title_to_tab = {}
        self._overplot = OverPlotState.off

        self._containers = [TabbedViewingArea(self, menuBar=menuBar) for _ in range(2)]
        layout = QVBoxLayout()
        for container in self._containers:
            layout.addWidget(container)
        self.setLayout(layout)

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
        target_area = self._containers[0]
        for entry in entries:
            uid = entry().metadata['start']['uid']
            if not self._run_to_tabs[uid]:
                # Add new Viewer tab.
                viewer = RunViewer(entry=entry)
                tab_title = uid[:8]
                index = target_area.addTab(viewer, tab_title)
                widget = target_area.widget(index)
                self._title_to_tab[tab_title] = widget
                self._run_to_tabs[uid].append(widget)

    def set_overplot_state(self, state):
        log.debug('Overplot state is %s', state)
        self.overplot = state

    def close_run_viewer(self, widget):
        self._run_to_tabs[widget.uid].remove(widget)


class TabbedViewingArea(MoveableTabWidget):
    """
    Contains RunViewers
    """
    def __init__(self, *args, menuBar, **kwargs):
        super().__init__(*args, **kwargs)
        self.setTabsClosable(True)
        self.tabCloseRequested.connect(self.close_tab)

    def close_tab(self, index):
        widget = self.widget(index)
        self.parent().close_run_viewer(widget)
        self.removeTab(index)


class RunViewer(QTabWidget):
    """
    Contains tabs showing various view on the data from one Run.
    """
    def __init__(self, *args, entry, **kwargs):
        super().__init__(*args, **kwargs)
        self.entry = entry
        self._uid = None
        self.run_router = RunRouter([
            BaselineFactory(self.addTab),
            HeaderTreeFactory(self.addTab),
            FigureManager(self.addTab),
            ])
        self.load()

    @property
    def uid(self):
        "Return RunStart UID."
        if self._uid is None:
            self._uid = self.entry().metadata['start']['uid']
        return self._uid

    def load(self):
        "Load all documents from intake and push them through the RunRouter."
        # TODO Put this on a thread.
        for name, doc in self.entry().read_canonical():
            self.run_router(name, doc)


class OverPlotState(enum.Enum):
    off = enum.auto()
    latest_live = enum.auto()
    fixed = enum.auto()
