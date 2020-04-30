from qtpy.QtWidgets import (
    QTabWidget,
    QHBoxLayout,
    QVBoxLayout,
    QToolBar,
    QMenu,
    QAction,
    QTreeView,
    QListView,
    QWidget,
    QSizePolicy,
    QTabBar,
)
from qtpy.QtCore import QObject, QAbstractItemModel, QSize, Qt, QEvent, Signal, QSettings
from qtpy.QtGui import QIcon, QPixmap, QKeyEvent
from intake.catalog.base import Catalog
from intake.catalog.entry import CatalogEntry
from ..clientonlymodels.LocalFileSystemResource import LocalFileSystemResourcePlugin
from xicam.gui.static import path
from xicam.core.data import NonDBHeader, load_header


from xicam.core import threads
from .searchlineedit import SearchLineEdit
from urllib import parse
from pathlib import Path
from functools import partial
import os, webbrowser
from xicam.gui.widgets.tabview import ContextMenuTabBar
from xicam.gui.bluesky.databroker_catalog_plugin import DatabrokerCatalogPlugin


class BrowserTabWidget(QTabWidget):
    def __init__(self, parent=None):
        super(BrowserTabWidget, self).__init__(parent)
        self.setContentsMargins(0, 0, 0, 0)


class DataBrowser(QWidget):
    sigOpen = Signal(NonDBHeader)
    sigPreview = Signal(NonDBHeader)

    def __init__(self, browserview):
        super(DataBrowser, self).__init__()

        hbox = QHBoxLayout()
        vbox = QVBoxLayout()
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.setSpacing(0)
        hbox.setContentsMargins(0, 0, 0, 0)
        hbox.setSpacing(0)
        self.setContentsMargins(0, 0, 0, 0)

        self.browserview = browserview
        self.browserview.sigOpen.connect(self.sigOpen)
        self.browserview.sigPreview.connect(self.sigPreview)
        self.browserview.sigOpenExternally.connect(self.openExternally)
        self.browserview.sigURIChanged.connect(self.uri_to_text)
        self.toolbar = QToolBar()
        self.toolbar.addAction(QIcon(QPixmap(str(path("icons/up.png")))), "Move up directory", self.moveUp)
        # self.toolbar.addAction(QIcon(QPixmap(str(path('icons/filter.png')))), 'Filter')
        self.toolbar.addAction(QIcon(QPixmap(str(path("icons/refresh.png")))), "Refresh", self.hardRefreshURI)
        self.toolbar.setToolButtonStyle(Qt.ToolButtonIconOnly)
        self.URILineEdit = SearchLineEdit("", clearable=False)
        self.uri_to_text()

        hbox.addWidget(self.toolbar)
        hbox.addWidget(self.URILineEdit)
        vbox.addLayout(hbox)
        vbox.addWidget(self.browserview)
        self.setLayout(vbox)

        self.URILineEdit.textChanged.connect(self.softRefreshURI)
        self.URILineEdit.returnPressed.connect(self.softRefreshURI)  # hard refresh
        self.URILineEdit.focusOutEvent = self.softRefreshURI  # hard refresh

        self.hardRefreshURI()

    def text_to_uri(self):
        uri = parse.urlparse(self.URILineEdit.text())
        self.browserview.model().uri = uri
        return uri

    def uri_to_text(self):
        uri = self.browserview.model().uri
        text = parse.urlunparse(uri)
        self.URILineEdit.setText(text)
        return text

    def hardRefreshURI(self, *_, **__):
        self.text_to_uri()
        self.browserview.refresh()

    def moveUp(self):
        self.browserview.model().uri = parse.urlparse(str(Path(self.URILineEdit.text()).parent))
        self.browserview.refresh()
        self.uri_to_text()

    def openExternally(self, uri):
        webbrowser.open(uri)

    softRefreshURI = hardRefreshURI


class BrowserTabBar(ContextMenuTabBar):
    sigAddBrowser = Signal(object, str)

    def __init__(self, tabwidget: QTabWidget):
        super(BrowserTabBar, self).__init__()

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
        tab = self.addTab(self.plusIcon, "")
        try:
            self.tabButton(tab, QTabBar.RightSide).resize(0, 0)
            self.tabButton(tab, QTabBar.RightSide).hide()
        except AttributeError:
            self.tabButton(tab, QTabBar.LeftSide).resize(0, 0)
            self.tabButton(tab, QTabBar.LeftSide).hide()
        # self.movePlusButton()  # Move to the correct location
        # self.setDocumentMode(True)
        self.currentChanged.connect(self.tabwidget.setCurrentIndex)
        self.currentChanged.connect(self.saveLastTab)
        self.installEventFilter(self)

    def saveLastTab(self, i):
        if i < 2:
            QSettings().setValue("databrowsertab", i)

    def addTab(self, *args, **kwargs):
        return self.insertTab(self.count() - 1, *args, **kwargs)

    def eventFilter(self, object, event):
        try:
            if (
                object == self
                and event.type() in [QEvent.MouseButtonPress, QEvent.MouseButtonRelease]
                and event.button() == Qt.LeftButton
            ):

                if event.type() == QEvent.MouseButtonPress:
                    tabIndex = object.tabAt(event.pos())
                    if tabIndex == self.count() - 1:
                        self.showMenu(self.mapToGlobal(event.pos()))
                        return True
            return False
        except Exception as e:
            print("Exception raised in eventfilter", e)

    def showMenu(self, pos):
        self.menu = QMenu()
        # Add all resource plugins
        self.actions = {}
        from xicam.plugins import manager as pluginmanager

        for plugin in pluginmanager.get_plugins_of_type("CatalogPlugin") + pluginmanager.get_plugins_of_type(
            "DataResourcePlugin"
        ):
            self.actions[plugin.name] = QAction(plugin.name)
            self.actions[plugin.name].triggered.connect(partial(self._addBrowser, plugin))
            self.menu.addAction(self.actions[plugin.name])

        self.menu.popup(pos)

    def _addBrowser(self, plugin):
        from xicam.plugins import DataResourcePlugin, CatalogPlugin

        plugin = plugin()

        if isinstance(plugin, DataResourcePlugin):
            datasource = plugin
            self.sigAddBrowser.emit(datasource.controller(datasource.view(datasource.model(datasource))), datasource.name)
        elif isinstance(plugin, Catalog):
            self.sigAddBrowser.emit(plugin.controller, plugin.name)


class DataResourceView(QObject):
    def __init__(self, model: QAbstractItemModel):
        super(DataResourceView, self).__init__()
        self._model = model  # type: QAbstractItemModel
        self.setModel(self._model)
        self.doubleClicked.connect(self.open)
        self.setSelectionMode(self.ExtendedSelection)
        self.setSelectionBehavior(self.SelectRows)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.menuRequested)

        self.menu = QMenu()
        standardActions = [
            QAction("Open", self),
            QAction("Open Externally", self),
            QAction("Enable/Disable Streaming", self),
            QAction("Delete", self),
        ]
        self.menu.addActions(standardActions)
        standardActions[0].triggered.connect(self.open)
        standardActions[1].triggered.connect(self.openExternally)

    def menuRequested(self, position):
        self.menu.exec_(self.viewport().mapToGlobal(position))

    def open(self, index):
        pass

    def currentChanged(self, current, previous):
        pass

    def openExternally(self, uri: str):
        pass


class DataResourceTree(QTreeView, DataResourceView):
    sigOpen = Signal(object)
    sigOpenPath = Signal(str)
    sigOpenExternally = Signal(str)
    sigPreview = Signal(object)
    sigURIChanged = Signal()

    def __init__(self, *args):
        super(DataResourceTree, self).__init__(*args)

    def refresh(self):
        self.model().refresh()
        self.setRootIndex(self.model().index(self.model().path))


class DataResourceList(QListView, DataResourceView):
    sigOpen = Signal(object)
    sigOpenPath = Signal(str)
    sigOpenExternally = Signal(str)
    sigPreview = Signal(object)
    sigURIChanged = Signal()

    def refresh(self):
        self.model().refresh()

    @threads.method()
    def open(self, _):
        indexes = self.selectionModel().selectedRows()
        if len(indexes) == 1:
            path = os.path.join(self.model().config["path"], self.model().data(indexes[0], Qt.DisplayRole).value())
            if self.model().isdir(indexes[0]):
                self.model().config["path"] = path
                self.sigURIChanged.emit()
                return
        uris = [self.model().pull(index) for index in indexes]
        header = load_header(uris=uris)
        if header:
            self.sigOpen.emit(header)


class LocalFileSystemTree(DataResourceTree):
    def __init__(self):
        super(LocalFileSystemTree, self).__init__(LocalFileSystemResourcePlugin())

    def open(self, _=None):
        indexes = self.selectionModel().selectedRows()
        if len(indexes) == 1:
            path = self.model().filePath(indexes[0])
            if os.path.isdir(path):
                self.model().path = path
                self.setRootIndex(indexes[0])
                self.sigURIChanged.emit()
                return
        self.sigOpen.emit(self.model().getHeader(indexes))

    def currentChanged(self, current, previous):
        if current.isValid():
            header = self.model().getHeader([current])
            if header:
                self.sigPreview.emit(header)

        self.scrollTo(current)

    def keyPressEvent(self, event: QKeyEvent):
        super(LocalFileSystemTree, self).keyPressEvent(event)
        if event.key() in [Qt.Key_Enter, Qt.Key_Return]:
            event.accept()
            self.open()

    def openExternally(self, uri: str):
        indexes = self.selectionModel().selectedRows()
        for index in indexes:
            self.sigOpenExternally.emit(self.model().filePath(index))


class DataResourceBrowser(QWidget):
    sigOpen = Signal(NonDBHeader)
    sigPreview = Signal(NonDBHeader)

    def __init__(self):
        super(DataResourceBrowser, self).__init__()
        vbox = QVBoxLayout()
        vbox.setSpacing(0)
        vbox.setContentsMargins(0, 0, 0, 0)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMinimumSize(QSize(250, 400))

        # cache pre-load index (otherwise it gets overwritten during init
        index = int(QSettings().value("databrowsertab", 0))

        self.browsertabwidget = BrowserTabWidget(self)
        self.browsertabbar = BrowserTabBar(self.browsertabwidget)
        self.browsertabbar.sigAddBrowser.connect(self.addBrowser)
        self.browsertabbar.tabCloseRequested.connect(self.closetab)

        # Add the required 'Local' browser
        self.addBrowser(DataBrowser(LocalFileSystemTree()), "Local", closable=False)
        self.addBrowser(DatabrokerCatalogPlugin().controller, "Databroker", closable=False)
        self.browsertabbar.setCurrentIndex(index)

        vbox.addWidget(self.browsertabwidget)

        self.setLayout(vbox)

    def closetab(self, i):
        if hasattr(self.browsertabwidget.widget(i), "closable"):
            if self.browsertabwidget.widget(i).closable:
                self.browsertabwidget.removeTab(i)

    def sizeHint(self):
        return QSize(250, 400)

    def addBrowser(self, databrowser: DataBrowser, text: str, closable: bool = True):
        databrowser.sigOpen.connect(self.sigOpen)
        databrowser.sigPreview.connect(self.sigPreview)
        databrowser.closable = closable
        tab = self.browsertabwidget.addTab(databrowser, text)
        self.browsertabwidget.setCurrentIndex(tab)
        # self.browsertabbar.addTab(text)
        if closable is False:
            try:
                self.browsertabbar.tabButton(tab, QTabBar.RightSide).resize(0, 0)
                self.browsertabbar.tabButton(tab, QTabBar.RightSide).hide()
            except AttributeError:
                self.browsertabbar.tabButton(tab, QTabBar.LeftSide).resize(0, 0)
                self.browsertabbar.tabButton(tab, QTabBar.LeftSide).hide()
