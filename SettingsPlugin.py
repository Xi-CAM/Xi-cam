from qtpy.QtCore import *
from qtpy.QtGui import *
from yapsy.IPlugin import IPlugin


class SettingsPlugin(QStandardItem, IPlugin):
    def __init__(self, icon, name):
        super(SettingsPlugin, self).__init__(icon, name)
        self.widget = None
        self.setTextAlignment(Qt.AlignHCenter)
        self.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
        self.setSizeHint(QSize(136, 80))

    def save(self):
        raise NotImplementedError

    def restore(self):
        raise NotImplementedError
