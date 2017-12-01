from qtpy.QtGui import *
from qtpy.QtWidgets import *
from xicam.gui.static import path

from xicam.plugins import SettingsPlugin


class VenvsSettingsPlugin(SettingsPlugin):
    name = 'Virtual Environments'

    def __init__(self):
        self.widget = QLabel('test')
        super(VenvsSettingsPlugin, self).__init__(QIcon(str(path('icons/python.png'))),
                                                  self.name,
                                                  self.widget)

    def save(self):
        return None  # self.parameter.saveState()

    def restore(self, state):
        pass  # self.parameter.restoreState(state)
