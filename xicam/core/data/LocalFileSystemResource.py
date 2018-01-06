from xicam.plugins import DataResourcePlugin
import sys, os

class LocalFileSystemResourcePlugin(DataResourcePlugin):

    def __init__(self):
        super(LocalFileSystemResourcePlugin, self).__init__()

        self.config['path'] = os.getcwd()
        if 'qtpy' in sys.modules:
            from qtpy.QtCore import QSettings
            self.config['path'] = QSettings().value('lastlocaldir')

    def dataChanged(self, topleft=None, bottomright=None):
        if self.model:
            self.model.dataChanged.emit(topleft, bottomright)

    def columnCount(self, index=None):
        raise NotImplementedError

    def rowCount(self, index=None):
        raise NotImplementedError

    def data(self, index, role):
        raise NotImplementedError

    def headerData(self, column, orientation, role):
        raise NotImplementedError

    def index(self, row, column, parent):
        raise NotImplementedError

    def parent(self, index):
        raise NotImplementedError

    @property
    def host(self): return self.config['host']
