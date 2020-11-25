# from abc import ABC, abstractmethod
import numpy as np
from pyqtgraph import ImageView, PlotWidget, ErrorBarItem
import pyqtgraph as pg
from qtpy.QtWidgets import QWidget, QComboBox, QVBoxLayout

from matplotlib import pyplot as plt
from xarray import DataArray

from xicam.core.intents import PlotIntent, ErrorBarIntent, BarIntent, PairPlotIntent
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


class XicamIntentCanvas(IntentCanvas):
    """Xi-CAM specific canvas."""
    def __init__(self, *args, **kwargs):
        super(XicamIntentCanvas, self).__init__(*args, **kwargs)
        self.intent_to_items = {}


class ImageIntentCanvas(XicamIntentCanvas, QWidget):
    def __init__(self, *args, **kwargs):
        super(ImageIntentCanvas, self).__init__(*args, **kwargs)
        self.setLayout(QVBoxLayout())
        self.canvas_widget = None

    def render(self, intent):
        if not self.canvas_widget:
            bases_names = intent.mixins or tuple()
            bases = map(lambda name: plugin_manager.type_mapping['ImageMixinPlugin'][name], bases_names)
            self.canvas_widget = type('ImageViewBlend', (*bases, ImageView), {})()
            self.layout().addWidget(self.canvas_widget)
            self.canvas_widget.imageItem.setOpts(imageAxisOrder='row-major')

        # TODO: add rendering logic for ROI intents
        return self.canvas_widget.setImage(np.asarray(intent.image).squeeze())

    def unrender(self, intent) -> bool:
        ...


class PlotIntentCanvasBlend(CurveLabels):
    ...


class PlotIntentCanvas(XicamIntentCanvas, QWidget):
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
                    item.setData(pen=color)

    def render(self, intent):
        if not self.canvas_widget:
            bases_names = intent.mixins or tuple()
            bases = map(lambda name: plugin_manager.type_mapping['PlotMixinPlugin'][name], bases_names)
            self.canvas_widget = type('PlotViewBlend', (*bases, PlotWidget), {})()
            self.layout().addWidget(self.canvas_widget)
            self.canvas_widget.plotItem.addLegend()

        items = []

        if isinstance(intent, (PlotIntent, ErrorBarIntent)):
            x = intent.x
            if intent.x is not None:
                x = np.asarray(intent.x).squeeze()

            plotitem = self.canvas_widget.plot(x=x, y=np.asarray(intent.y).squeeze(), name=intent.item_name)
            # Use most recent intent's log mode for the canvas's log mode
            x_log_mode = intent.kwargs.get("xLogMode", self.canvas_widget.plotItem.getAxis("bottom").logMode)
            y_log_mode = intent.kwargs.get("yLogMode", self.canvas_widget.plotItem.getAxis("left").logMode)

            self.canvas_widget.plotItem.setLogMode(x=x_log_mode, y=y_log_mode)
            self.canvas_widget.setLabels(**intent.labels)

            items.append(plotitem)

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


class PairPlotIntentCanvas(XicamIntentCanvas, QWidget):
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
