from typing import Dict, List
import copy
from itertools import count

import numpy as np
import pyqtgraph as pg
from qtpy.QtGui import QTransform

from xicam.gui.widgets.dynimageview import DynImageView
from xicam.gui.widgets.plotwidgetmixins import CurveLabels


class Hint(object):
    canvas_cls = None

    def __init__(self, **kwargs):
        self.parent = None
        self.checked = False
        self.enabled = True
        self._name = None

    def init_canvas(self, **kwargs):
        return self.canvas_cls()

    @property
    def name(self):
        raise NotImplementedError

    def remove(self):
        raise NotImplementedError

    def selective_copy(self, var_mapping: Dict):
        # TODO raise
        return self

    def visualize(self, canvas):
        raise NotImplementedError


class PlotHint(Hint):
    canvas_cls = CurveLabels

    def __init__(self, x: np.ndarray, y: np.ndarray, xLog: bool = False, yLog: bool = False, labels=None, **kwargs):
        super(PlotHint, self).__init__()
        if kwargs.get("name"):
            self._name = kwargs["name"]
        self.x = x
        self.y = y
        self.kwargs = kwargs
        self.item = None
        self.canvas = None
        self.xLog = xLog
        self.yLog = yLog
        self.labels = labels

    def init_canvas(self, addLegend=False, **kwargs):
        canvas = super(PlotHint, self).init_canvas(**kwargs)
        if addLegend:
            canvas.addLegend(offset=(-1, 1))
        return canvas

    @property
    def name(self):
        if not self._name:
            left = self.kwargs.get("labels", dict()).get("left")
            bottom = self.kwargs.get("labels", dict()).get("bottom")
            if left and bottom:
                self._name = f"{left} vs. {bottom}"
            else:
                self._name = "Plot"
        return self._name

    def visualize(self, canvas, color=None):
        plotItem = canvas.plotItem
        plotItem.setLabels(**(self.labels or {}))
        plotItem.setLogMode(x=self.xLog, y=self.yLog)
        if self.kwargs.get("name"):
            self.item = canvas.plot(self.x, self.y, **self.kwargs)
        else:
            self.item = canvas.plot(self.x, self.y, name=self._name, **self.kwargs)
        self.canvas = canvas

        style = self.kwargs.get("style")
        # Update colors according to number of plot data items in the canvas
        if not color:
            numItems = len(plotItem.items)
            for i in range(numItems):
                color = (float(i) / numItems * 255, (1 - float(i) / numItems) * 255, 255)
                plotItem.items[i].setPen(color, **self.kwargs)
        else:
            self.item.setPen(color, **self.kwargs)

    def remove(self):
        legend = self.canvas.plotItem.legend
        if legend:
            # Don't rely on pg.LegendItem.removeItem, as it uses str comparison (instead of refs) to remove!
            # legend.removeItem(self.name)
            for sample, label in legend.items:
                if sample.item is self.item:
                    legend.items.remove((sample, label))
                    legend.layout.removeItem(sample)
                    sample.close()
                    legend.layout.removeItem(label)
                    label.close()
                    legend.updateSize()
        self.canvas.removeItem(self.item)
        self.item = None
        if not list(filter(lambda item: isinstance(item, pg.PlotCurveItem), self.canvas.items())):
            parent_widget = self.canvas.parent().parent()
            parent_widget.removeTab(parent_widget.indexOf(self.canvas))

    def selective_copy(self, var_mapping: Dict):
        new_plot_hint = copy.copy(self)
        new_plot_hint.x = var_mapping[self.x]
        new_plot_hint.y = var_mapping[self.y]
        return new_plot_hint


class VerticalROI(Hint):
    # Design needs to be thought out here, could be either a plot widget or image view
    # TODO -- range should not be a Var
    # canvas_cls = tuple(pg.PlotWidget, pg.ImageView)

    def __init__(self, range: str, **kwargs):
        super(VerticalROI, self).__init__()
        self.range = range
        self.kwargs = kwargs
        self.canvas = None

    @property
    def name(self):
        return f"{self.parent.name} Vertical ROI"

    def visualize(self, canvas):  # TODO: callables?
        from pyqtgraph import LinearRegionItem

        self.canvas = canvas
        self.canvas.addItem(LinearRegionItem(*self.range.value, **self.kwargs))

    @property
    def name(self):
        return f"{self.parent.name} Vertical ROI"


class ImageHint(Hint):
    # TODO -- change to DynImageView (address quickMinMax when resizing the two-time image)
    canvas_cls = DynImageView
    ref_count = count(0)

    def __init__(
        self, image, name="", invertY=False, xlabel: str = None, ylabel: str = None, transform=None, z: int = None, **kwargs
    ):
        self._name = name
        super(ImageHint, self).__init__()
        self.count = next(self.ref_count)
        self.image = image
        self.invertY = invertY
        self.xlabel = xlabel
        self.ylabel = ylabel
        self.transform = transform
        if transform is None:
            transform = QTransform()
            transform.translate(0, -1)
            transform.scale(0, -1)
            self.transform = transform
        self.z = z
        self.kwargs = kwargs
        self.enabled = False
        self.canvas = None

    def init_canvas(self, **kwargs):
        self.canvas = self.canvas_cls(view=pg.PlotItem(labels=dict(left=self.xlabel, bottom=self.ylabel)))
        self.canvas.view.invertY(self.invertY)
        return self.canvas

    @property
    def name(self):
        if not self._name:
            self._name = "Image " + str(self.count)
        return self._name

    def visualize(self, canvas):
        self.canvas = canvas
        self.canvas.setImage(self.image, **self.kwargs)

    def remove(self):
        parent_widget = self.canvas.parent().parent()
        parent_widget.removeTab(parent_widget.indexOf(self.canvas))

    def selective_copy(self, var_mapping: Dict):
        new_plot_hint = copy.copy(self)
        new_plot_hint.image = var_mapping[self.image]
        return new_plot_hint


class CoPlotHint(Hint):
    canvas_cls = CurveLabels
    canvas_map = dict()

    def __init__(self, *plothints: List[PlotHint], **kwargs):
        if kwargs.get("name"):
            self._name = kwargs["name"]
        super(CoPlotHint, self).__init__()
        self.plothints = [*plothints]  # type: List[PlotHint]
        self.kwargs = kwargs
        self.canvas = None

    def init_canvas(self, addLegend=False, **kwargs):
        canvas = super(CoPlotHint, self).init_canvas(**kwargs)
        self.canvas_map[canvas] = 0
        if addLegend:
            canvas.addLegend(offset=(-1, 1))
        return canvas

    @property
    def name(self):
        if not self._name:
            self._name = f"Plot of " + ", ".join([hint.name for hint in self.plothints])
        return self._name

    def remove(self):
        for plothint in self.plothints:
            plothint.remove()
        self.canvas_map[self.canvas] -= 1
        if self.canvas_map[self.canvas] < 0:
            self.canvas_map[self.canvas] = 0

    def visualize(self, canvas):
        self.canvas = canvas
        self.canvas_map[self.canvas] += 1
        numItems = self.canvas_map[self.canvas]
        # Update colors according to number of co-plot hints in the same canvas
        for i in range(numItems):
            color = (float(i) / numItems * 255, (1 - float(i) / numItems) * 255, 255)
        for plothint in self.plothints:
            # TODO: should this rely on the contained plothints' visualize? or should we directly plot on the canvas?
            plothint.visualize(self.canvas, color=color)
            # self.canvas.plot(plothint.x, plothint.y, **{**plothint.kwargs, **self.kwargs})
