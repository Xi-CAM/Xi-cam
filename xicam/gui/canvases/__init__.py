# from abc import ABC, abstractmethod
import numpy as np
from pyqtgraph import ImageView, PlotWidget, ErrorBarItem
import pyqtgraph as pg

from matplotlib import pyplot as plt
from xarray import DataArray

from xicam.core.intents import PlotIntent, ErrorBarIntent

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


class ImageIntentCanvas(XicamIntentCanvas, ImageView):
    def __init__(self, *args, **kwargs):
        super(ImageIntentCanvas, self).__init__(*args, **kwargs)

    def render(self, intent):
        # TODO: add rendering logic for ROI intents
        return self.setImage(np.asarray(intent.image).squeeze())

    def unrender(self, intent) -> bool:
        ...


class PlotIntentCanvasBlend(CurveLabels):
    ...


class PlotIntentCanvas(XicamIntentCanvas, PlotIntentCanvasBlend):
    def __init__(self, *args, **kwargs):
        # Intercept kwargs that we want to control PlotWidget behavior
        # Get the x & y log mode (default false, which is linear)
        x_log_mode = kwargs.pop("xLogMode", False)
        y_log_mode = kwargs.pop("yLogMode", False)

        super(PlotIntentCanvas, self).__init__(*args, **kwargs)

        self.plotItem.addLegend()
        self.setLogMode(x=x_log_mode, y=y_log_mode)
        self.setLabels(**kwargs.get("labels", {}))

    def colorize(self):
        count = len(self.intent_to_items)
        for i, items in enumerate(self.intent_to_items.values()):
            if count < 9:
                color = pg.mkColor(i)
            else:
                color = pg.intColor(i, hues=count, minHue=180, maxHue=300)

            for item in items:
                item.setData(pen=color)

    def render(self, intent):
        items = []

        if isinstance(intent, (PlotIntent, ErrorBarIntent)):

            plotitem = self.plot(x=np.asarray(intent.x).squeeze(), y=np.asarray(intent.y).squeeze(), name=intent.item_name)
            # Use most recent intent's log mode for the canvas's log mode
            x_log_mode = intent.kwargs.get("xLogMode", self.plotItem.getAxis("bottom").logMode)
            y_log_mode = intent.kwargs.get("yLogMode", self.plotItem.getAxis("left").logMode)
            self.plotItem.setLogMode(x=x_log_mode, y=y_log_mode)
            self.setLabels(**intent.labels)

            items.append(plotitem)

        if isinstance(intent, ErrorBarIntent):
            kwargs = intent.kwargs.copy()
            for key, value in kwargs.items():
                if isinstance(value, DataArray):
                    kwargs[key] = np.asanyarray(value).squeeze()
            erroritem = ErrorBarItem(x=np.asarray(intent.x).squeeze(), y=np.asarray(intent.y).squeeze(), **kwargs)
            self.plotItem.addItem(erroritem)

            items.append(erroritem)

        self.intent_to_items[intent] = items
        self.colorize()
        return items

    def unrender(self, intent) -> bool:
        """Un-render the intent from the canvas and return if the canvas can be removed."""
        if intent in self.intent_to_items:
            items = self.intent_to_items[intent]
            for item in items:
                self.plotItem.removeItem(item)
            del self.intent_to_items[intent]
            self.colorize()

        if not self.intent_to_items:
            return True

        return False
