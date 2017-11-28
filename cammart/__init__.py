import requests
from qtpy.QtCore import *
from qtpy.QtGui import *
from qtpy.QtWidgets import *

from xicam.gui.static import path
from xicam.gui.widgets.searchlineedit import SearchLineEdit
from xicam.plugins import SettingsPlugin
from xicam.plugins import cammart


class CamMartSettingsPlugin(SettingsPlugin):
    name = 'Plugins'

    def __init__(self):
        self.widget = QWidget()
        self.widget.setLayout(QHBoxLayout())
        self.listview = QListView()
        self.plugintoolbar = QToolBar()
        self.plugintoolbar.setOrientation(Qt.Vertical)
        self.plugintoolbar.addAction(QIcon(str(path('icons/plus.png'))),
                                     'Add plugin',
                                     self.addplugin)
        self.plugintoolbar.addAction(QIcon(str(path('icons/minus.png'))),
                                     'Remove plugin',
                                     self.removeplugin)
        self.widget.layout().addWidget(self.listview)
        self.widget.layout().addWidget(self.plugintoolbar)
        super(CamMartSettingsPlugin, self).__init__(QIcon(str(path('icons/python.png'))),
                                                    self.name,
                                                    self.widget)

    def addplugin(self):
        self._dialog = CamMartInstallDialog()
        self._dialog.show()

    def removeplugin(self):
        pass

    def save(self):
        return None  # self.parameter.saveState()

    def restore(self, state):
        pass  # self.parameter.restoreState(state)


repositories = ['localhost:5000']


class CamMartInstallDialog(QDialog):
    def __init__(self):
        super(CamMartInstallDialog, self).__init__()

        self.packagesWidget = QListView()
        # self.packagesWidget.setViewMode(QListView.Mode)
        # self.contentsWidget.setIconSize(QSize(96, 84))
        self.packagesWidget.setMovement(QListView.Static)
        # self.packagesWidget.setMaximumWidth(174)
        # self.packagesWidget.setSpacing(12)
        self.packagesWidget.setSelectionMode(QAbstractItemView.SingleSelection)

        self.packagesModel = QStandardItemModel()
        self.packagesWidget.setModel(self.packagesModel)
        self.packageInfoWidget = PackageInfoWidget(self.packagesWidget)
        self.packagesWidget.selectionModel().currentChanged.connect(self.packageInfoWidget.refresh)

        self.installButton = QPushButton("&Install Package")
        self.manageButton = QPushButton("&Manage Repositories")
        self.installButton.clicked.connect(self.install)
        self.manageButton.clicked.connect(self.manage)

        self.buttonboxWidget = QDialogButtonBox()
        self.buttonboxWidget.addButton(self.installButton, QDialogButtonBox.ActionRole)
        self.buttonboxWidget.addButton(self.manageButton, QDialogButtonBox.ActionRole)

        splitter = QSplitter()
        splitter.addWidget(self.packagesWidget)
        splitter.addWidget(self.packageInfoWidget)

        self.searchbox = SearchLineEdit()

        mainLayout = QVBoxLayout()
        mainLayout.addWidget(self.searchbox)
        mainLayout.addWidget(splitter)
        mainLayout.addSpacing(12)
        mainLayout.addWidget(self.buttonboxWidget)

        self.setLayout(mainLayout)
        self.setWindowTitle("Install Packages...")

        self.refresh()

    def refresh(self):
        self.packagesModel.clear()
        for repo in repositories:
            # TODO: check behavior for >25 items (pagesize)
            for packageinfo in eval(requests.get(f'http://{repo}/pluginpackages').content)["_items"]:
                item = QStandardItem(packageinfo['name'])
                item.info = packageinfo
                self.packagesModel.appendRow(item)

    def install(self):
        cammart.install(self.packagesModel.itemFromIndex(self.packagesWidget.selectedIndexes()[0]).text())

    def manage(self):
        pass


class PackageInfoWidget(QTextEdit):
    def __init__(self, view):
        super(PackageInfoWidget, self).__init__()

        self.view = view

    def refresh(self, current, previous):
        info = self.view.model().itemFromIndex(current).info
        self.setText(
            f"""
            <h1>{info['name']}</h1>
            <p>{info['documentation'].get('description')}</p>
            <p>Version: {info['documentation'].get('version')}</p>
            <p>Authors: {", ".join(info['documentation'].get('authors'))}</p>
            <p>Publication: {info['documentation'].get('publication')}</p>
            <p>Reference: {info['documentation'].get('reference')}</p>
            <p>Keywords: {", ".join(info['documentation'].get('keywords'))}</p>
            """)
        #
        # self.description
        # self.keywords
        # self.authors
        # self.version
        # self.reference
        # self.publication
        # self.installuri
        # self.plugins
