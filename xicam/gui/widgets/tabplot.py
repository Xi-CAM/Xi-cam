import pyqtgraph as pg
from qtpy.QtWidgets import QTabWidget
from typing import List


class TabPlotWidget(QTabWidget):
    def __init__(self):
        super(TabPlotWidget, self).__init__()

    def plot(self, *args, **kwargs):
        plotwidget = pg.PlotWidget(*args, **kwargs)
        self.addTab(kwargs.get("title", "Untitled"), plotwidget)

    @property
    def plots(self) -> List[pg.PlotWidget]:
        return [self.widget(i) for i in range(self.count())]
