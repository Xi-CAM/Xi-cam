# from abc import ABC, abstractmethod
import numpy as np
from pyqtgraph import ImageView, PlotWidget
import pyqtgraph as pg


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
        self.intent_to_item = {}


class ImageIntentCanvas(XicamIntentCanvas, ImageView):
    def __init__(self, *args, **kwargs):
        super(ImageIntentCanvas, self).__init__(*args, **kwargs)

    def render(self, intent):
        # TODO: add rendering logic for ROI intents
        return self.setImage(np.asarray(intent.image))

    def unrender(self, intent) -> bool:
        ...


# (not priority - why is racoon sometimes rotated 90? (depending on os)
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
        count = len(self.intent_to_item)
        for i, item in enumerate(self.intent_to_item.values()):
            if count < 9:
                color = pg.mkColor(i)
            else:
                color = pg.intColor(i, hues=count, minHue=180, maxHue=300)

            item.setPen(color)

    def render(self, intent):
        plot_item = self.plot(x=np.asarray(intent.x).squeeze(), y=np.asarray(intent.y).squeeze(), name=intent.item_name)
        # Use most recent intent's log mode for the canvas's log mode
        x_log_mode = intent.kwargs.get("xLogMode", self.plotItem.getAxis("bottom").logMode)
        y_log_mode = intent.kwargs.get("yLogMode", self.plotItem.getAxis("left").logMode)
        self.plotItem.setLogMode(x=x_log_mode, y=y_log_mode)

        self.setLabels(**intent.labels)

        self.intent_to_item[intent] = plot_item

        self.colorize()
        return plot_item

    def unrender(self, intent) -> bool:
        """Un-render the intent from the canvas and return if the canvas can be removed."""
        if intent in self.intent_to_item:
            item = self.intent_to_item[intent]
            self.plotItem.removeItem(item)
            del self.intent_to_item[intent]
            self.colorize()

        if len(self.intent_to_item.items()) == 0:
            return True

        return False
