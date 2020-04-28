from qtpy.QtCore import *
from qtpy.QtWidgets import *
from .plugin import PluginType


class ControllerPlugin(QWidget, PluginType):
    needs_qt = True
    is_singleton = False

    def __init__(self, device, parent=None, *args):
        self.device = device
        PluginType.__init__(self)
        QWidget.__init__(
            self, parent, *args
        )  # TODO: Strange MRO, not sure why QWidget init isn't being called; replaced by IPlugin init twice?
