from qtpy.QtWidgets import *
from qtpy.QtCore import *
from qtpy.QtGui import *
from ..clientonlymodels.LocalFileSystemResource import LocalFileSystemResourcePlugin
from xicam.gui.static import path
from .searchlineedit import SearchLineEdit
import urllib.parse
import os

class DataResourceBrowser(QWidget):
    def __init__(self):
        super(DataResourceBrowser, self).__init__()
        hbox = QHBoxLayout()
        vbox = QVBoxLayout()


        self.browsertabbar = BrowserTabBar(self)
        self.URILineEdit = SearchLineEdit(QSettings().value('lastlocaldir'))
        self.optionsButton = QPushButton('...')
        self.refreshButton = QPushButton('o')
        self.dataResourceTabs = QTabWidget()
        self.dataResourceTree = LocalFileSystemTree(LocalFileSystemResourcePlugin())
        self.dataResourceTabs.addTab(self.dataResourceTree, 'Local')

        vbox.addWidget(self.browsertabbar)
        hbox.addWidget(self.URILineEdit)
        hbox.addWidget(self.optionsButton)
        hbox.addWidget(self.refreshButton)
        vbox.addLayout(hbox)
        vbox.addWidget(self.dataResourceTabs)
        self.setLayout(vbox)

        self.URILineEdit.textChanged.connect(self.softRefreshURI)
        self.URILineEdit.returnPressed.connect(self.softRefreshURI)  # hard refresh
        self.URILineEdit.focusOutEvent = self.softRefreshURI  # hard refresh
        self.refreshButton.clicked.connect(self.hardRefreshURI)

        self.hardRefreshURI()

    def hardRefreshURI(self, *_, **__):
        currentView = self.dataResourceTabs.currentWidget()
        uri = urllib.parse.urlparse(self.URILineEdit.text())
        config = currentView.model.config
        config['scheme'] = uri.scheme
        config['host'] = uri.netloc
        config['path'] = uri.path
        config['query'] = uri.query
        config['fragment'] = uri.fragment
        config['user'] = uri.username
        config['port'] = uri.port
        config['password'] = uri.password
        print('config:',config)
        currentView.refresh()

        # TODO: move other widgets into new subwidget class


    softRefreshURI = hardRefreshURI

class BrowserTabBar(QTabBar):
    sigAddBrowser = Signal()

    def __init__(self, parent=None):
        super(BrowserTabBar, self).__init__(parent)

        plusPixmap = QPixmap(str(path("icons/plus.png")))
        self.plusIcon = QIcon(plusPixmap)
        # self.plus_button.setToolTip('Open a new browser')
        # self.plus_button.setParent(self)
        # self.plus_button.setMaximumSize(32, 32)
        # self.plus_button.setMinimumSize(32, 32)
        # self.plus_button.clicked.connect(self.sigAddBrowser.emit)
        self.addTab(self.plusIcon, '')
        # self.movePlusButton()  # Move to the correct location
        # self.setDocumentMode(True)

class DataResourceMixin(QWidget):
    sigOpen = Signal(list)
    sigOpenPath = Signal(str)
    sigItemPreview = Signal(str)



class DataResourceTree(QTreeView, DataResourceMixin):
    def __init__(self, model):
        super(DataResourceTree, self).__init__()
        self.model = model
        self.setModel(self.model)
        self.doubleClicked.connect(self.open)

    def refresh(self):
        self.model.refresh()
        self.setRootIndex(self.model.index(self.model.path))

    def open(self, index):
        pass


class LocalFileSystemTree(DataResourceTree):

    def open(self, index):
        path = self.model.filePath(index)
        if os.path.isdir(path):
            self.model.path = path
            self.setRootIndex(index)
        else:
            self.sigOpen.emit(self.model.getHeader(index))