from .ProcessingPlugin import Output


class Hint(object):
    def __init__(self, **kwargs):
        self.parent = None
        self.checked = False

    @property
    def name(self):
        raise NotImplementedError


class PlotHint(Hint):
    def __init__(self, x: Output, y: Output):
        super(PlotHint, self).__init__()
        self.x = x
        self.y = y

    @property
    def name(self):
        return f"{self.y.name} vs. {self.x.name}"
