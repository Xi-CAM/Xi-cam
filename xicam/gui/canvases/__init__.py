from abc import ABC, abstractmethod
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


class ImageIntentCanvas(ImageView):
    def __init__(self, *args, **kwargs):
        super(ImageIntentCanvas, self).__init__(*args, **kwargs)

    def render(self, intent):
        return self.setImage(intent.image)

    def unrender(self, intent):
        pass


class PlotIntentCanvas(PlotWidget):
    def __init__(self, *args, **kwargs):
        super(PlotIntentCanvas, self).__init__(*args, **kwargs)

    def render(self, intent):#):
        return self.plot(x=intent.x.compute(), y=intent.y.compute())

    def unrender(self, intent):
        ...


class MatplotlibImageCanvas(ImageIntentCanvas):
    def render(self, intent):
        return plt.imshow(intent.image)

    def unrender(self, intent):
        pass


plot_canvas = PlotIntentCanvas


if __name__ == "__main__":
    import numpy as np
    from qtpy.QtWidgets import QApplication
    from xicam.core.intents import ImageIntent, PlotIntent

    app = QApplication([])

    widget = QWidget()
    canvas = MatplotlibImageCanvas()
    img = np.random.random(size=(100, 100))
    intent = ImageIntent(image=img)
    canvas.render()

    app.exec()