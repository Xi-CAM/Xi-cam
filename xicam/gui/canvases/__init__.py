# from abc import ABC, abstractmethod
from copy import copy
from typing import List

import numpy as np
from pyqtgraph import ImageView, PlotWidget, ErrorBarItem, ScatterPlotItem
import pyqtgraph as pg
from qtpy.QtCore import Signal
from qtpy.QtWidgets import QWidget, QComboBox, QVBoxLayout

from matplotlib import pyplot as plt
from xarray import DataArray

from xicam.core.intents import PlotIntent, ErrorBarIntent, BarIntent, PairPlotIntent, ROIIntent, ScatterIntent
from xicam.gui.actions import Action
from xicam.plugins import manager as plugin_manager

# IntentCanvas -> SingleIntentCanvas -> ImageIntentCanvas
#              -> MultipleIntentCanvas -> PlotItentCanvas

# IntentCanvas.serialize() -> raise NIE
# IntentCanvas.deserialize() -> raise NIE
# not implemented for most derived classes


# How do we be friendly to Jupyter land?
# Use a manager object that sits above Xi-cam land and Generic land
# manager object has a standardized interface for dispatching intents to canvases
# Xi-cam: ProxyModel
# JupyterLand: whatever implements that interface


# # TODO: fix TypeError: metaclass conflict: the metaclass of a derived class must be a (non-strict) subclass of the metaclasses of all its bases
# # class IntentCanvas(ABC):
# class IntentCanvas(PluginType):
#     def __init__(self):
#         pass
#     #     # self._intents = []
#
#     # @abstractmethod
#     def render(self, intent):
#         pass
#
#     # @abstractmethod
#     def unrender(self, intent):
#         pass
from xicam.gui.widgets.plotwidgetmixins import CurveLabels
from xicam.plugins.intentcanvasplugin import IntentCanvas


class _XicamIntentCanvas(IntentCanvas, QWidget):
    """Xi-CAM specific canvas."""
    def __init__(self, *args, **kwargs):
        super(_XicamIntentCanvas, self).__init__(*args, **kwargs)
        self.intent_to_items = {}


class XicamIntentCanvas(_XicamIntentCanvas):
    sigInteractiveAction = Signal(Action, _XicamIntentCanvas)


class ImageIntentCanvas(XicamIntentCanvas):
    def __init__(self, *args, **kwargs):
        super(ImageIntentCanvas, self).__init__(*args, **kwargs)
        self.setLayout(QVBoxLayout())
        self.canvas_widget = None
        # Store the "image" intent, since we will have roi and overlay intents as well
        self._primary_intent = None

    def render(self, intent, mixins: List[str] = None):
        """Render an intent to the canvas.

        Optionally, provide additional list of mixin names to extend the image canvas functionality.
        """
        # Extract and remove labels (if provide) kwarg and pass to the widget __init__
        # labels kwarg should only be provided by the AxesLabels mixin
        kwargs = getattr(intent, "kwargs", {}).copy()
        constructor_kwargs = dict()
        labels_kwarg = kwargs.pop("labels", None)
        if labels_kwarg:
            constructor_kwargs["labels"] = labels_kwarg
        if not self.canvas_widget:
            bases_names = getattr(intent, "mixins", None) or tuple()
            if mixins:
                bases_names += tuple(mixins)
            # Place in dict to remove duplicates
            bases = dict(map(lambda name: (plugin_manager.type_mapping['ImageMixinPlugin'][name], 0), bases_names))
            self.canvas_widget = type('ImageViewBlend', (*bases.keys(), ImageView), {})(**constructor_kwargs)
            self.layout().addWidget(self.canvas_widget)
            self.canvas_widget.imageItem.setOpts(imageAxisOrder='row-major')

        for key, value in kwargs.items():
            if isinstance(value, DataArray):
                kwargs[key] = np.asanyarray(value).squeeze()

        if hasattr(intent, 'geometry'):
            kwargs['geometry'] = intent.geometry

        if hasattr(intent, 'incidence_angle'):
            kwargs['incidence_angle'] = intent.incidence_angle
            kwargs['geometry_mode'] = 'reflection'

        if isinstance(intent, ROIIntent):
            self.canvas_widget.view.addItem(intent.roi)
        else:
            self.canvas_widget.setImage(intent.image.squeeze(), **kwargs)
            self._primary_intent = intent

    def unrender(self, intent) -> bool:
        """Return True if the canvas can be removed."""
        if self.canvas_widget:
            if isinstance(intent, ROIIntent):
                self.canvas_widget.view.removeItem(intent.roi)
                return False
        return True


class PlotIntentCanvasBlend(CurveLabels):
    ...


class PlotIntentCanvas(XicamIntentCanvas):
    def __init__(self, *args, **kwargs):
        super(PlotIntentCanvas, self).__init__(*args, **kwargs)

        self.setLayout(QVBoxLayout())
        self.canvas_widget = None

    def colorize(self):
        count = len(self.intent_to_items)
        for i, items in enumerate(self.intent_to_items.values()):
            if count < 9:
                color = pg.mkColor(i)
            else:
                color = pg.intColor(i, hues=count, minHue=180, maxHue=300)

            for item in items:
                if isinstance(item, pg.PlotDataItem):
                    item.setData(pen=color, symbolBrush=color, symbolPen='w')

    def render(self, intent):
        if not self.canvas_widget:
            bases_names = getattr(intent, 'mixins', tuple()) or tuple()
            bases = map(lambda name: plugin_manager.type_mapping['PlotMixinPlugin'][name], bases_names)
            self.canvas_widget = type('PlotViewBlend', (*bases, PlotIntentCanvasBlend), {})()
            self.layout().addWidget(self.canvas_widget)
            self.canvas_widget.plotItem.addLegend()

        items = []

        if isinstance(intent, (PlotIntent, ErrorBarIntent, ScatterIntent)):
            x = intent.x
            if intent.x is not None:
                x = np.asarray(intent.x).squeeze()

            ys = np.asarray(intent.y).squeeze()
            if ys.ndim == 1:
                ys = [ys]
                multicurves = False
            else:
                multicurves = True

            symbol = intent.kwargs.get("symbol", None)

            for i in range(len(ys)):
                name = intent.name
                if multicurves:
                    name += f' {i + 1}'

                if isinstance(intent, ScatterIntent):
                    item = ScatterPlotItem(x=x, y=ys[i], name=name, symbol=symbol)
                    self.canvas_widget.plotItem.addItem(item)
                elif isinstance(intent, (PlotIntent, ErrorBarIntent)):
                    item = self.canvas_widget.plot(x=x, y=ys[i], name=name, symbol=symbol)
                items.append(item)

            # Use most recent intent's log mode for the canvas's log mode
            x_log_mode = intent.kwargs.get("xLogMode", self.canvas_widget.plotItem.getAxis("bottom").logMode)
            y_log_mode = intent.kwargs.get("yLogMode", self.canvas_widget.plotItem.getAxis("left").logMode)
            self.canvas_widget.plotItem.setLogMode(x=x_log_mode, y=y_log_mode)
            self.canvas_widget.setLabels(**intent.labels)

        if isinstance(intent, ErrorBarIntent):
            kwargs = intent.kwargs.copy()
            for key, value in kwargs.items():
                if isinstance(value, DataArray):
                    kwargs[key] = np.asanyarray(value).squeeze()
            erroritem = ErrorBarItem(x=np.asarray(intent.x).squeeze(), y=np.asarray(intent.y).squeeze(), **kwargs)
            self.canvas_widget.plotItem.addItem(erroritem)

            items.append(erroritem)

        elif isinstance(intent, BarIntent):
            kwargs = intent.kwargs.copy()
            for key, value in kwargs.items():
                if isinstance(value, DataArray):
                    kwargs[key] = np.asanyarray(value).squeeze()
            if intent.x is not None:
                kwargs['x'] = intent.x
            baritem = pg.BarGraphItem(**kwargs)
            self.canvas_widget.plotItem.addItem(baritem)

            items.append(baritem)

        self.intent_to_items[intent] = items
        self.colorize()
        return items

    def unrender(self, intent) -> bool:
        """Un-render the intent from the canvas and return if the canvas can be removed."""
        if intent in self.intent_to_items:
            items = self.intent_to_items[intent]
            for item in items:
                self.canvas_widget.plotItem.removeItem(item)
            del self.intent_to_items[intent]
            self.colorize()

        if not self.intent_to_items:
            return True

        return False


class PairPlotIntentCanvas(XicamIntentCanvas):
    def __init__(self, *args, **kwargs):
        super(PairPlotIntentCanvas, self).__init__()
        self.transform_data = None

        self.plot_widget = PlotIntentCanvasBlend()
        self.plot_widget.setAspectLocked(True)
        self.componentA = QComboBox()
        self.componentB = QComboBox()

        self.setLayout(QVBoxLayout())
        self.layout().addWidget(self.plot_widget)
        self.layout().addWidget(self.componentA)
        self.layout().addWidget(self.componentB)

        # Signals
        self.componentA.currentIndexChanged.connect(self.show_pair)
        self.componentB.currentIndexChanged.connect(self.show_pair)

    def render(self, intent: PairPlotIntent):
        n_components = intent.transform_data.shape[-1]
        for i in range(n_components):
            self.componentA.addItem(f'Component {i+1}')
            self.componentB.addItem(f'Component {i + 1}')

        self.transform_data = intent.transform_data

    def show_pair(self):
        if self.transform_data is not None:
            A = self.componentA.currentIndex()
            B = self.componentB.currentIndex()

            A_data = np.asarray(self.transform_data[:, :, A]).ravel()
            B_data = np.asarray(self.transform_data[:, :, B]).ravel()

            self.plot_widget.clear()
            item = pg.ScatterPlotItem(x=B_data, y=A_data)
            self.plot_widget.addItem(item)
            self.plot_widget.setLabels(left=f'Component {A+1}', bottom=f'Component {B+1}')
