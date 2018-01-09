from qtpy.QtWidgets import *
from qtpy.QtCore import *
from qtpy.QtGui import *
from ..clientonlymodels.LocalFileSystemResource import LocalFileSystemResourcePlugin
from xicam.gui.static import path
from xicam.core.data import NonDBHeader
from .searchlineedit import SearchLineEdit
from urllib import parse
from pathlib import Path
import os




class BrowserTabWidget(QTabWidget):
    def __init__(self, parent=None):
        super(BrowserTabWidget, self).__init__(parent)
        self.setContentsMargins(0,0,0,0)

class BrowserTabBar(QTabBar):
    sigAddBrowser = Signal()

    def __init__(self, tabwidget:QTabWidget, parent=None):
        super(BrowserTabBar, self).__init__(parent)

        self.tabwidget = tabwidget
        self.tabwidget.setTabBar(self)

        self.setExpanding(False)
        self.setTabsClosable(True)

        plusPixmap = QPixmap(str(path("icons/plus.png")))
        self.plusIcon = QIcon(plusPixmap)
        # self.plus_button.setToolTip('Open a new browser')
        # self.plus_button.setParent(self)
        # self.plus_button.setMaximumSize(32, 32)
        # self.plus_button.setMinimumSize(32, 32)
        # self.plus_button.clicked.connect(self.sigAddBrowser.emit)
        tab = self.addTab(self.plusIcon, '')
        try:
            self.tabButton(tab, QTabBar.RightSide).resize(0, 0)
            self.tabButton(tab, QTabBar.RightSide).hide()
        except AttributeError:
            self.tabButton(tab, QTabBar.LeftSide).resize(0, 0)
            self.tabButton(tab, QTabBar.LeftSide).hide()
        # self.movePlusButton()  # Move to the correct location
        # self.setDocumentMode(True)
        self.currentChanged.connect(self.tabwidget.setCurrentIndex)
        self.installEventFilter(self)

    def addTab(self, *args, **kwargs):
        return self.insertTab(self.count()-1,*args,**kwargs)

    def eventFilter(self, object, event):
        try:
            if object == self and event.type() in [QEvent.MouseButtonPress,
                                                   QEvent.MouseButtonRelease] and event.button() == Qt.LeftButton:

                if event.type() == QEvent.MouseButtonPress:
                    tabIndex = object.tabAt(event.pos())
                    if tabIndex == self.count()-1:
                        return True
            return False
        except Exception as e:
            print("Exception raised in eventfilter", e)


class DataBrowser(QWidget):
    sigOpen = Signal(NonDBHeader)

    def __init__(self, browserview):
        super(DataBrowser, self).__init__()

        hbox = QHBoxLayout()
        vbox = QVBoxLayout()
        vbox.setContentsMargins(0,0,0,0)
        vbox.setSpacing(0)
        hbox.setContentsMargins(0,0,0,0)
        hbox.setSpacing(0)
        self.setContentsMargins(0,0,0,0)

        self.browserview = browserview
        self.browserview.sigOpen.connect(self.sigOpen)
        self.browserview.sigConfigChanged.connect(self.pushConfigtoURI)
        self.toolbar = QToolBar()
        self.toolbar.addAction(QIcon(QPixmap(str(path('icons/up.png')))), 'Move up directory', self.moveUp)
        # self.toolbar.addAction(QIcon(QPixmap(str(path('icons/filter.png')))), 'Filter')
        self.toolbar.addAction(QIcon(QPixmap(str(path('icons/refresh.png')))), 'Refresh', self.hardRefreshURI)
        self.toolbar.setToolButtonStyle(Qt.ToolButtonIconOnly)
        self.URILineEdit = SearchLineEdit('',clearable=False)
        self.pushConfigtoURI()

        hbox.addWidget(self.toolbar)
        hbox.addWidget(self.URILineEdit)
        vbox.addLayout(hbox)
        vbox.addWidget(self.browserview)
        self.setLayout(vbox)

        self.URILineEdit.textChanged.connect(self.softRefreshURI)
        self.URILineEdit.returnPressed.connect(self.softRefreshURI)  # hard refresh
        self.URILineEdit.focusOutEvent = self.softRefreshURI  # hard refresh

        self.hardRefreshURI()

    def pushURItoConfig(self):
        uri = parse.urlparse(self.URILineEdit.text())
        config = self.browserview.model.config
        config['scheme'] = uri.scheme
        config['host'] = uri.netloc
        config['path'] = uri.path
        config['query'] = uri.query
        config['fragment'] = uri.fragment
        config['params'] = uri.params
        config['user'] = uri.username
        config['port'] = uri.port
        config['password'] = uri.password
        print('config:', config)
        return config

    def pushConfigtoURI(self):
        config = self.browserview.model.config
        uri = parse.ParseResult(scheme=config.get('scheme',''),
                                netloc=config.get('host',''),
                                path=config.get('path',''),
                                params=config.get('params',''),
                                query=config.get('query',''),
                                fragment=config.get('fragment',''))
        uri = parse.urlunparse(uri)
        self.URILineEdit.setText(uri)
        return config


    def hardRefreshURI(self, *_, **__):
        self.pushURItoConfig()
        self.browserview.refresh()

    def moveUp(self):
        config = self.pushURItoConfig()
        config['path'] = str(Path(config['path']).parent)
        self.browserview.refresh()
        self.pushConfigtoURI()

    softRefreshURI = hardRefreshURI



class DataResourceTree(QTreeView):
    sigOpen = Signal(NonDBHeader)
    sigOpenPath = Signal(str)
    sigItemPreview = Signal(str)

    def __init__(self, model):
        super(DataResourceTree, self).__init__()
        self.model = model
        self.setModel(self.model)
        self.doubleClicked.connect(self.open)
        self.setSelectionMode(self.ExtendedSelection)
        self.setSelectionBehavior(self.SelectRows)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.menuRequested)

        self.menu = QMenu()
        standardActions = [QAction('Open', self),
                           QAction('Open Externally', self),
                           QAction('Enable/Disable Streaming'),
                           QAction('Delete', self)]
        self.menu.addActions(standardActions)
        standardActions[0].triggered.connect(self.open)

    def menuRequested(self, position):
        self.menu.exec_(self.viewport().mapToGlobal(position))

    def refresh(self):
        self.model.refresh()
        self.setRootIndex(self.model.index(self.model.path))

    def open(self, index):
        pass


class LocalFileSystemTree(DataResourceTree):
    sigConfigChanged = Signal()

    def __init__(self):
        self.model = LocalFileSystemResourcePlugin()
        super(LocalFileSystemTree, self).__init__(self.model)

    def open(self, _):
        indexes = self.selectionModel().selectedRows()
        if len(indexes)==1:
            path = self.model.filePath(indexes[0])
            if os.path.isdir(path):
                self.model.path = path
                self.setRootIndex(indexes[0])
                self.sigConfigChanged.emit()
                return

        indexes = self.selectionModel().selectedRows()
        self.sigOpen.emit(self.model.getHeader(indexes))

class DataResourceBrowser(QWidget):
    sigOpen = Signal(NonDBHeader)

    def __init__(self):
        super(DataResourceBrowser, self).__init__()
        vbox = QVBoxLayout()
        vbox.setSpacing(0)
        vbox.setContentsMargins(0,0,0,0)

        self.browsertabwidget = BrowserTabWidget(self)
        self.browsertabbar = BrowserTabBar(self.browsertabwidget, self)
        self.addBrowser(DataBrowser(LocalFileSystemTree()), 'Local', closable=False)
        self.browsertabbar.setCurrentIndex(0)

        vbox.addWidget(self.browsertabwidget)

        self.setLayout(vbox)

        self.sigOpen.connect(print)

    def addBrowser(self, databrowser:DataBrowser, text:str, closable:bool=True):
        databrowser.sigOpen.connect(self.sigOpen)
        tab = self.browsertabwidget.addTab(databrowser, text)
        # self.browsertabbar.addTab(text)
        if closable is False:
            try:
                self.browsertabbar.tabButton(tab, QTabBar.RightSide).resize(0, 0)
                self.browsertabbar.tabButton(tab, QTabBar.RightSide).hide()
            except AttributeError:
                self.browsertabbar.tabButton(tab, QTabBar.LeftSide).resize(0, 0)
                self.browsertabbar.tabButton(tab, QTabBar.LeftSide).hide()