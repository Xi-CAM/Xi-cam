import logging

from event_model import RunRouter
from matplotlib.backends.backend_qt5agg import (
    FigureCanvasQTAgg as FigureCanvas,
    NavigationToolbar2QT as NavigationToolbar)
import matplotlib
from qtpy.QtWidgets import (  # noqa
    QLabel,
    QWidget,
    QVBoxLayout,
    )
from traitlets.traitlets import Bool, List, Set
from traitlets.config import Configurable

from ...heuristics.utils import hinted_fields, guess_dimensions  # noqa
from ...heuristics.line import LinePlotManager
from ...heuristics.image import LatestFrameImageManager
from ...utils import load_config

matplotlib.use('Qt5Agg')  # must set before importing matplotlib.pyplot
import matplotlib.pyplot as plt  # noqa


log = logging.getLogger('bluesky_browser')


class FigureManager(Configurable):
    """
    For a given Viewer, encasulate the matplotlib Figures and associated tabs.
    """
    factories = List([
        LinePlotManager,
        LatestFrameImageManager],
        config=True)
    enabled = Bool(True, config=True)
    exclude_streams = Set([], config=True)

    def __init__(self, add_tab):
        self.update_config(load_config())
        self.add_tab = add_tab
        self._figures = {}

    def get_figure(self, key, label, *args, **kwargs):
        try:
            return self._figures[key]
        except KeyError:
            return self._add_figure(key, label, *args, **kwargs)

    def _add_figure(self, key, label, *args, **kwargs):
        tab = QWidget()
        fig, _ = plt.subplots(*args, **kwargs)
        canvas = FigureCanvas(fig)
        canvas.setMinimumWidth(640)
        canvas.setParent(tab)
        toolbar = NavigationToolbar(canvas, tab)
        tab_label = QLabel(label)
        tab_label.setMaximumHeight(20)

        layout = QVBoxLayout()
        layout.addWidget(tab_label)
        layout.addWidget(canvas)
        layout.addWidget(toolbar)
        tab.setLayout(layout)
        self.add_tab(tab, label)
        self._figures[key] = fig
        return fig

    def __call__(self, name, start_doc):
        if not self.enabled:
            return [], []
        dimensions = start_doc.get('hints', {}).get('dimensions', guess_dimensions(start_doc))
        rr = RunRouter(
            [factory(self, dimensions) for factory in self.factories])
        rr('start', start_doc)
        return [rr], []
