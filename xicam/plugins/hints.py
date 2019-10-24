from .processingplugin import Var, Input, ProcessingPlugin
from typing import Dict, List
import copy


class Hint(object):
    def __init__(self, **kwargs):
        self.parent = None
        self.checked = False
        self.enabled = True

    @property
    def name(self):
        raise NotImplementedError

    def selective_copy(self, var_mapping: Dict):
        #TODO raise
        return self


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

    def selective_copy(self, var_mapping: Dict):
        new_plot_hint = copy.copy(self)
        new_plot_hint.x = var_mapping[self.x]
        new_plot_hint.y = var_mapping[self.y]
        return new_plot_hint


class VerticalROI(Hint):
    def __init__(self, range: Var, **kwargs):
        super(VerticalROI, self).__init__()
        self.range = range
        self.kwargs = kwargs

    @property
    def name(self):
        return f"{self.parent.name} Vertical ROI"

    def visualize(self, canvas, **canvases):  # TODO: callables?
        from pyqtgraph import LinearRegionItem

        canvas = canvases["imageview"]
        if callable(canvas):
            canvas = canvas()
        canvas.addItem(LinearRegionItem(*self.range.value, **self.kwargs))

    @property
    def name(self):
        return f"{self.parent.name} Vertical ROI"


class ButtonHint(Hint):
    targetattribute = "value"

    def __init__(self, activated: Var, iconpath: str):
        super(ButtonHint, self).__init__()
        self.activated = activated
        self.iconpath = iconpath
        self.enabled = False

    def visualize(self, canvas, **canvases):
        from qtpy.QtWidgets import QToolButton
        from qtpy.QtGui import QIcon

        canvas = canvases["toolbar"]  # type:QToolBar
        if callable(canvas):
            canvas = canvas()
        button = QToolButton()
        button.setIcon(QIcon(self.iconpath))
        button.setCheckable(True)
        button.toggled.connect(lambda state: setattr(self.activated, self.targetattribute, state))
        canvas.addWidget(button)

    @property
    def name(self):
        return f"{self.activated.name} button"


class EnableHint(ButtonHint):
    targetattribute = "enabled"

    def __init__(self, parent: ProcessingPlugin, iconpath: str):
        super(EnableHint, self).__init__(parent, iconpath)  # Ignore typing violation
        self.iconpath = iconpath
        self.enabled = False  # This 'enabled' means the hint's visibility can't be changed

    @property
    def name(self):
        return f"{self.parent.name} toggle button"


class ImageHint(Hint):
    def __init__(self, image: Var, xlabel: str = None, ylabel: str = None, transform=None, z: int = None, **kwargs):
        super(ImageHint, self).__init__()
        self.image = image
        self.xlabel = xlabel
        self.ylabel = ylabel
        self.transform = transform
        self.z = z
        self.kwargs = kwargs
        self.enabled = False

    @property
    def name(self):
        return f"Image of {self.image.name}"

    def visualize(self, canvas, **canvases):
        canvas = canvases["imageview"]
        if canvas:
            canvas.setImage(self.image.value, **self.kwargs)

    def selective_copy(self, var_mapping: Dict):
        new_plot_hint = copy.copy(self)
        new_plot_hint.image = var_mapping[self.image]
        return new_plot_hint


class CoPlotHint(Hint):
    def __init__(self, *plothints: List[PlotHint], **kwargs):
        super(CoPlotHint, self).__init__()
        self.plothints = plothints  # type: List[PlotHint]
        self.kwargs = kwargs

    @property
    def name(self):
        return f"Plot of " + ", ".join([hint.name for hint in self.plothints])

    def visualize(self, canvas, **canvases):
        for plothint in self.plothints:
            canvas.plot(plothint.x, plothint.y, **{**plothint.kwargs, **self.kwargs})
