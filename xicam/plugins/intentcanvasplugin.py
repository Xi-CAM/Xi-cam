from . import PluginType


# TODO : ABC inherit
class IntentCanvas(object):

    def __init__(self, name=None, *args, **kwargs):
        super(IntentCanvas, self).__init__(*args, **kwargs)
        self._name = name

    def render(self, intent):
        ...

    def unrender(self, intent) -> bool:
        ...

    @property
    def name(self):
        return self._name


class IntentCanvasPlugin(PluginType, IntentCanvas):
    ...


