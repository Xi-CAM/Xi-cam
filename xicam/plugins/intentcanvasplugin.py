from . import PluginType


# TODO : ABC inherit
class IntentCanvas:
    def render(self, intent):
        ...

    def unrender(self, intent):
        ...


class IntentCanvasPlugin(PluginType, IntentCanvas):
    ...


