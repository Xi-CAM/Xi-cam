from abc import ABC, abstractmethod
import numpy as np
from pyqtgraph import ImageView, PlotWidget
from matplotlib import pyplot as plt


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
from xicam.plugins.intentcanvasplugin import IntentCanvas


class XicamIntentCanvas(IntentCanvas):
    """Xi-CAM specific canvas."""
    def __init__(self, *args, **kwargs):
        name = kwargs.pop('name', None)
        if not name:
            name = args[-1]
        super(XicamIntentCanvas, self).__init__(name)
        self.intent_to_item = {}


class ImageIntentCanvas(XicamIntentCanvas, ImageView):
    def __init__(self, *args, **kwargs):
        super(ImageIntentCanvas, self).__init__(*args, **kwargs)

    def render(self, intent):
        # TODO: add rendering logic for ROI intents
        return self.setImage(intent.image)

    def unrender(self, intent) -> bool:
        ...


class PlotIntentCanvas(XicamIntentCanvas, PlotWidget):
    def __init__(self, *args, **kwargs):
        super(PlotIntentCanvas, self).__init__(*args, **kwargs)

    def render(self, intent):
        plot_item = self.plot(x=np.asarray(intent.x), y=np.asarray(intent.y))
        self.intent_to_item[intent] = plot_item
        return plot_item

    def unrender(self, intent) -> bool:
        """Un-render the intent from the canvas and return if the canvas can be removed."""
        if intent in self.intent_to_item:
            item = self.intent_to_item[intent]
            self.plotItem.removeItem(item)
            del self.intent_to_item[intent]

        if len(self.intent_to_item.items()) == 0:
            return True

        return False


class MatplotlibImageCanvas(ImageIntentCanvas):
    def render(self, intent):
        return plt.imshow(intent.image)

    def unrender(self, intent):
        pass


if __name__ == "__main__":
    import numpy as np
    from qtpy.QtWidgets import QApplication, QWidget
    from xicam.core.intents import ImageIntent, PlotIntent

    app = QApplication([])

    widget = QWidget()
    canvas = MatplotlibImageCanvas()
    img = np.random.random(size=(100, 100))
    intent = ImageIntent(image=img)
    canvas.render()

    app.exec()