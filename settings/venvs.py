from qtpy.QtGui import *
from qtpy.QtWidgets import *

from xicam.gui.static import path
from xicam.plugins import SettingsPlugin


class VenvsSettingsPlugin(SettingsPlugin):
    def __init__(self):
        super(VenvsSettingsPlugin, self).__init__(QIcon(str(path('icons/python.png'))),
                                                  'Virtual Environments')
        self.widget = QLabel('test')
