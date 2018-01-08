from xicam.plugins import DataResourcePlugin
import sys, os

if 'qtpy' in sys.modules:
    from qtpy.QtWidgets import *
    from qtpy.QtCore import QSettings, QDir


    class LocalFileSystemResourcePlugin(QFileSystemModel):

        def __init__(self):
            super(LocalFileSystemResourcePlugin, self).__init__()

            self.config = {'path': QSettings().value('lastlocaldir', os.getcwd())}

            self.setRootPath(self.config['path'])

        def setRootPath(self, path):
            if os.path.isdir(path):
                filter = '*'
                root = path
            else:
                filter = os.path.basename(path)
                root = path[:-len(filter)]

            root = QDir(root)
            super(LocalFileSystemResourcePlugin, self).setRootPath(root.absolutePath())
            self.setNameFilters([filter])
            self.config['path'] = path
            QSettings().setValue('lastlocaldir', path)

        @property
        def path(self):
            return self.rootPath()

        @path.setter
        def path(self, value):
            self.setRootPath(value)

        def refresh(self):
            self.setRootPath(self.config['path'])