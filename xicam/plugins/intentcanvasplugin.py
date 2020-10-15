from . import PluginType


# TODO : ABC inherit
class IntentCanvas(object):

    def __init__(self, canvas_name="", *args, **kwargs):
        super(IntentCanvas, self).__init__(*args, **kwargs)
        self._canvas_name = canvas_name

    def render(self, intent):
        ...

    def unrender(self, intent) -> bool:
        ...

    @property
    def canvas_name(self):
        return self._canvas_name


class IntentCanvasPlugin(PluginType, IntentCanvas):
    ...


