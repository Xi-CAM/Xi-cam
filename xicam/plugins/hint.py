from .ProcessingPlugin import Var, Input
from typing import List


class Hint(object):
    def __init__(self, **kwargs):
        self.parent = None
        self.checked = False

    @property
    def name(self):
        raise NotImplementedError


class PlotHint(Hint):
    def __init__(self, x: Var, y: Var, **kwargs):
        super(PlotHint, self).__init__()
        self.x = x
        self.y = y
        self.kwargs = kwargs

    @property
    def name(self):
        return f"{self.y.name} vs. {self.x.name}"

    def visualize(self, canvas, **canvases):
        canvas.plot(self.x.value, self.y.value, **self.kwargs)


class ImageHint(Hint):
    def __init__(self, arr: Var, **kwargs):
        super(ImageHint, self).__init__()
        self.arr = arr
        self.kwargs = kwargs

    def visualize(self, canvas, **canvases):
        canvases['imageview'].setImage(self.arr.value, **self.kwargs)


class VerticalROI(Hint):
    def __init__(self, min: Var, max: Var, **kwargs):
        super(VerticalROI, self).__init__()
        self.min = min
        self.max = max
        self.kwargs = kwargs

    def visualize(self, canvas, **canvases):  # TODO: callables?
        from pyqtgraph import LinearRegionItem
        canvas = canvases['imageview']
        if callable(canvas): canvas = canvas()
        canvas.addItem(LinearRegionItem([self.min.value, self.max.value], **self.kwargs))


class ButtonHint(Hint):
    def __init__(self, activated: Var, iconpath):
        super(ButtonHint, self).__init__()
        self.activated = activated
        self.iconpath = iconpath

    def visualize(self, canvas, **canvases):
        from qtpy.QtWidgets import QToolButton
        from qtpy.QtGui import QIcon
        canvas = canvases['toolbar']  # type:QToolBar
        if callable(canvas): canvas = canvas()
        button = QToolButton()
        button.setIcon(QIcon(self.iconpath))
        button.setCheckable(True)
        button.toggled.connect(lambda state: setattr(self.activated, 'value', state))
        canvas.addWidget(button)


class CoPlotHint(Hint):
    def __init__(self, *plothints: List[PlotHint], **kwargs):
        super(CoPlotHint, self).__init__()
        self.plothints = plothints
        self.kwargs = kwargs

    def visualize(self, canvas, **canvases):
        for plothint in self.plothints:
            canvas.plot(plothint.x, plothint.y, **{**plothint.kwargs, **self.kwargs})
