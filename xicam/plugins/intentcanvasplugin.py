from . import PluginType


# TODO : ABC inherit
class IntentCanvas:

    def render(self, intent):
        ...

    def unrender(self, intent) -> bool:
        ...


class IntentCanvasPlugin(PluginType, IntentCanvas):
    ...


