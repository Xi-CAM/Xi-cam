from abc import ABC
from pyqtgraph import ImageView, PlotWidget


# View should destroy / disown canvases when they have no Intents.
# widget.setParent(None)


# CanvasView's model is the proxyModel (attached to tree source model)
# CanvasView manages canvases
# Canvases it will display are the top 4 in the proxy model (e.g)
# Using selected layout, puts canvas widgets into layout
# needs bookkeeping for the canvas widgets (if layout changes)


class IntentCanvas(ABC):
    def __init__(self):
        self._intents = []

    def render(self, intent):
        raise NotImplementedError

    def unrender(self, intent):
        raise NotImplementedError


class ImageIntentCanvas(ImageView, IntentCanvas):
    def __init__(self, *args, **kwargs):
        super(ImageIntentCanvas, self).__init__(*args, **kwargs)

    def render(self, intent):
        return self.setImage(intent.image)

    def unrender(self, intent):
        pass


class PlotIntentCanvas(PlotWidget, IntentCanvas):
    def __init__(self, *args, **kwargs):
        super(PlotIntentCanvas, self).__init__(*args, **kwargs)

    def render(self, intent):
        return self.plot(x=intent.x.compute(), y=intent.y.compute())

    def unrender(self, intent):
        pass


if __name__ == "__main__":
    from qtpy.QtWidgets import QApplication
    app = QApplication([])
    ih = ImageIntentCanvas()
    ph = PlotIntentCanvas()
    print(ih._intents)
    print(ph._intents)
    app.exec()