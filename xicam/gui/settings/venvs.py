from qtpy.QtGui import *
from qtpy.QtWidgets import *
from xicam.gui.static import path

from xicam.plugins import SettingsPlugin


class VenvsSettingsPlugin(SettingsPlugin):
    def __init__(self):
        self.widget = QLabel("test")
        super(VenvsSettingsPlugin, self).__init__(QIcon(str(path("icons/python.png"))), "Virtual Environments", self.widget)

    def toState(self):
        return None  # self.parameter.saveState()

    def fromState(self, state):
        pass  # self.parameter.restoreState(state)
