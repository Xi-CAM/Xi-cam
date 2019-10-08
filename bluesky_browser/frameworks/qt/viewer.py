import collections
import enum
from functools import partial
import itertools
import logging

from event_model import RunRouter, Filler
from databroker.core import parse_handler_registry
from qtpy.QtCore import Signal, Qt, QThread
from qtpy.QtWidgets import (
    QAction,
    QActionGroup,
    QInputDialog,
    QSplitter,
    QVBoxLayout,
)
from traitlets.traitlets import List, Dict, DottedObjectName, Integer

from .header_tree import HeaderTreeFactory
from .baseline import BaselineFactory
from .figures import FigureManager
from .utils import (
    MoveableTabWidget,
    ConfigurableMoveableTabContainer,
    ConfigurableQTabWidget,
)
from ...utils import load_config


log = logging.getLogger('bluesky_browser')


class Viewer(ConfigurableMoveableTabContainer):
    """
    Contains multiple TabbedViewingAreas
    """
    tab_titles = Signal([tuple])
    num_viewing_areas = Integer(2, config=True)

    def __init__(self, *args, menuBar, **kwargs):
        super().__init__(*args, **kwargs)
        self._run_to_tabs = collections.defaultdict(list)
        self._title_to_tab = {}
        self._tabs_from_streaming = []
        self._overplot = OverPlotState.individual_tab
        self._overplot_target = None
        self._live_enabled = False

        self._live_run_router = RunRouter([self.route_live_stream])

        self._containers = [TabbedViewingArea(viewer=self, menuBar=menuBar)
                            for _ in range(self.num_viewing_areas)]
        layout = QVBoxLayout()
        splitter = QSplitter(Qt.Vertical)
        layout.addWidget(splitter)
        for container in self._containers:
            splitter.addWidget(container)
        self.setLayout(layout)

        overplot_group = QActionGroup(self)
        self.off = QAction('&Off', self)
        self.off.setStatusTip('Drop streaming data.')
        self.individual_tab = QAction('&New Tab', self)
        self.individual_tab.setStatusTip('Open a new viewer tab for each Run.')
        self.latest_live = QAction('&Latest Live Tab', self)
        self.latest_live.setStatusTip('Attempt to overplot on the most recent live Run.')
        self.fixed = QAction('&Fixed Tab...', self)
        self.fixed.setStatusTip('Attempt to overplot on a specific tab.')
        self.fixed.setEnabled(False)
        overplot_group.addAction(self.off)
        overplot_group.addAction(self.individual_tab)
        overplot_group.addAction(self.latest_live)
        overplot_group.addAction(self.fixed)
        for action in overplot_group.actions():
            action.setCheckable(True)
        overplot_group.setExclusive(True)
        self.off.setChecked(True)

        overplot_menu = menuBar().addMenu('&Streaming')
        overplot_menu.addActions(overplot_group.actions())

        self.off.triggered.connect(self.disable_live)
        self.individual_tab.triggered.connect(partial(self.set_overplot_state, OverPlotState.individual_tab))
        self.latest_live.triggered.connect(partial(self.set_overplot_state, OverPlotState.latest_live))

        def set_overplot_target():
            item, ok = QInputDialog.getItem(
                self, "Select Tab", "Tab", tuple(self._title_to_tab), 0, False)
            if not ok:
                # Abort and fallback to Off. Would be better to fall back to
                # previous state (which could be latest_live) but it's not
                # clear how to know what that state was.
                self.off.setChecked(True)
                return
            self.set_overplot_state(OverPlotState.fixed)
            self._overplot_target = item

        self.fixed.triggered.connect(set_overplot_target)

    def enable_live(self):
        self._live_enabled = True

    def disable_live(self):
        self._live_enabled = False

    def consumer(self, item):
        """Slot that receives (name, doc) and unpacks it into RunRouter."""
        self._live_run_router(*item)

    def route_live_stream(self, name, start_doc):
        """Create or choose a Viewer to receive this Run."""
        if not self._live_enabled:
            log.debug("Streaming Run ignored because Streaming is disabled.")
            return [], []
        self.fixed.setEnabled(True)
        target_area = self._containers[0]
        uid = start_doc['uid']
        if self._overplot == OverPlotState.individual_tab:
            viewer = RunViewer()
            tab_title = uid[:8]
            index = target_area.addTab(viewer, tab_title)
            self._title_to_tab[tab_title] = viewer
            self._tabs_from_streaming.append(viewer)
            target_area.setCurrentIndex(index)
            self.tab_titles.emit(tuple(self._title_to_tab))
        elif self._overplot == OverPlotState.fixed:
            viewer = self._title_to_tab[self._overplot_target]
        elif self._overplot == OverPlotState.latest_live:
            if self._tabs_from_streaming:
                viewer = self._tabs_from_streaming[-1]
            else:
                viewer = RunViewer()
                tab_title = uid[:8]
                index = target_area.addTab(viewer, tab_title)
                self._title_to_tab[tab_title] = viewer
                self._tabs_from_streaming.append(viewer)
                target_area.setCurrentIndex(index)
                self.tab_titles.emit(tuple(self._title_to_tab))
        self._run_to_tabs[uid].append(viewer)
        viewer.run_router('start', start_doc)

        return [viewer.run_router], []

    def show_entries(self, target, entries):
        self.fixed.setEnabled(True)
        target_area = self._containers[0]
        if not target:
            # Add new Viewer tab.
            viewer = RunViewer()
            if len(entries) == 1:
                entry, = entries
                uid = entry.describe()['metadata']['start']['uid']
                tab_title = uid[:8]
            else:
                tab_title = self.get_title()
            index = target_area.addTab(viewer, tab_title)
            self._title_to_tab[tab_title] = viewer
            target_area.setCurrentIndex(index)
            self.tab_titles.emit(tuple(self._title_to_tab))
        else:
            viewer = self._title_to_tab[target]
        for entry in entries:
            viewer.load_entry(entry)
            uid = entry.describe()['metadata']['start']['uid']
            self._run_to_tabs[uid].append(viewer)
        # TODO Make last entry in the list the current widget.

    def get_title(self):
        for i in itertools.count(1):
            title = f'Group {i}'
            if title in self._title_to_tab:
                continue
            return title

    def set_overplot_state(self, state):
        self.enable_live()
        log.debug('Overplot state is %s', state)
        self._overplot = state

    def close_run_viewer(self, widget):
        try:
            self._tabs_from_streaming.remove(widget)
        except ValueError:
            pass
        for uid in widget.uids:
            self._run_to_tabs[uid].remove(widget)
            for title, tab in list(self._title_to_tab.items()):
                if tab == widget:
                    del self._title_to_tab[title]
                    self.tab_titles.emit(tuple(self._title_to_tab))
                    if title == self._overplot_target:
                        self.set_overplot_state(OverPlotState.off)
        if not self._title_to_tab:
            self.fixed.setEnabled(False)


class TabbedViewingArea(MoveableTabWidget):
    """
    Contains RunViewers
    """
    def __init__(self, *args, menuBar, viewer, **kwargs):
        super().__init__(*args, **kwargs)
        self.viewer = viewer
        self.setTabsClosable(True)
        self.tabCloseRequested.connect(self.close_tab)

    def close_tab(self, index):
        widget = self.widget(index)
        self.viewer.close_run_viewer(widget)
        self.removeTab(index)


class RunViewer(ConfigurableQTabWidget):
    """
    Contains tabs showing various view on the data from one Run.
    """
    factories = List([HeaderTreeFactory,
                      BaselineFactory,
                      FigureManager], config=True)
    handler_registry = Dict(DottedObjectName(), config=True)

    def __init__(self, *args, **kwargs):
        self.update_config(load_config())
        super().__init__(*args, **kwargs)
        self._entries = []
        self._uids = []
        self._active_loaders = set()

        def filler_factory(name, doc):
            filler = Filler(parse_handler_registry(self.handler_registry),
                            inplace=True)
            filler('start', doc)
            return [filler], []

        self.run_router = RunRouter(
            [filler_factory] +
            [factory(self.addTab) for factory in self.factories])

    @property
    def entries(self):
        return self._entries

    @property
    def uids(self):
        return self._uids

    def load_entry(self, entry):
        "Load all documents from databroker and push them through the RunRouter."
        self._entries.append(entry)
        self._uids.append(entry.describe()['metadata']['start']['uid'])
        entry_loader = EntryLoader(entry, self._active_loaders)
        entry_loader.signal.connect(self.run_router)
        entry_loader.start()


class EntryLoader(QThread):
    signal = Signal([str, dict])

    def __init__(self, entry, loaders, *args, **kwargs):
        self.entry = entry
        self.loaders = loaders
        self.loaders.add(self)  # Keep it safe from gc.
        self._datasource = None
        super().__init__(*args, **kwargs)

    @property
    def datasource(self):
        # Ensure that entry.get() is called only once.
        if self._datasource is None:
            self._datasource = self.entry.get()
        return self._datasource

    def run(self):
        for name, doc in self.datasource.read_canonical():
            self.signal.emit(name, doc)
        self.loaders.remove(self)


class OverPlotState(enum.Enum):
    individual_tab = enum.auto()
    latest_live = enum.auto()
    fixed = enum.auto()
