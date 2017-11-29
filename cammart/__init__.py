import requests
from qtpy.QtCore import *
from qtpy.QtGui import *
from qtpy.QtWidgets import *

from xicam.gui.static import path
from xicam.gui.widgets.searchlineedit import SearchLineEdit
from xicam.plugins import SettingsPlugin
from xicam.plugins import cammart


class CamMartSettingsPlugin(SettingsPlugin):
    """
    A built-in settings plugin to configure installed packages
    """
    name = 'Plugins'

    def __init__(self):
        # Setup UI
        self.widget = QWidget()
        self.widget.setLayout(QHBoxLayout())
        self.listview = QListView()
        self.packagesmodel = QStandardItemModel()
        self.listview.setModel(self.packagesmodel)

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

        self.refresh()

    def refresh(self):
        for name, scheme in cammart.pkg_registry.items():
            self.packagesmodel.appendRow(QStandardItem(name))

    def addplugin(self):
        # Open the CamMart install dialog
        self._dialog = CamMartInstallDialog()
        self._dialog.show()

    def removeplugin(self):
        cammart.uninstall(self.packagesmodel.itemFromIndex(self.listview.selectedIndexes()[0]).text())

    def save(self):
        return None  # self.parameter.saveState()

    def restore(self, state):
        pass  # self.parameter.restoreState(state)


repositories = ['localhost:5000']


class CamMartInstallDialog(QDialog):
    def __init__(self):
        super(CamMartInstallDialog, self).__init__()

        # Setup ListView
        self.packagesWidget = QListView()
        self.packagesWidget.setMovement(QListView.Static)
        self.packagesWidget.setSelectionMode(QAbstractItemView.SingleSelection)

        # Setup Model
        self.packagesModel = QStandardItemModel()
        self.packagesWidget.setModel(self.packagesModel)
        self.packageInfoWidget = PackageInfoWidget(self.packagesWidget)
        self.packagesWidget.selectionModel().currentChanged.connect(self.packageInfoWidget.refresh)

        # Setup dialog buttons
        self.installButton = QPushButton("&Install Package")
        self.manageButton = QPushButton("&Manage Repositories")
        self.installButton.clicked.connect(self.install)
        self.manageButton.clicked.connect(self.manage)
        self.buttonboxWidget = QDialogButtonBox()
        self.buttonboxWidget.addButton(self.installButton, QDialogButtonBox.ActionRole)
        self.buttonboxWidget.addButton(self.manageButton, QDialogButtonBox.ActionRole)

        # Setup splitter layout
        splitter = QSplitter()
        splitter.addWidget(self.packagesWidget)
        splitter.addWidget(self.packageInfoWidget)

        # Setup search box
        self.searchbox = SearchLineEdit()

        # Compose main layout
        mainLayout = QVBoxLayout()
        mainLayout.addWidget(self.searchbox)
        mainLayout.addWidget(splitter)
        mainLayout.addSpacing(12)
        mainLayout.addWidget(self.buttonboxWidget)
        self.setLayout(mainLayout)
        self.setWindowTitle("Install Packages...")

        # Load packages into view
        self.refresh()

    def refresh(self):
        # Clear model
        self.packagesModel.clear()

        # For each repo
        for repo in repositories:
            # TODO: check behavior for >25 items (pagesize)
            # For each package
            for packageinfo in eval(requests.get(f'http://{repo}/pluginpackages').content)["_items"]:
                # Add an item to the model
                item = QStandardItem(packageinfo['name'])
                item.info = packageinfo
                self.packagesModel.appendRow(item)

    def install(self):
        # Install the selected package using cammart
        cammart.install(self.packagesModel.itemFromIndex(self.packagesWidget.selectedIndexes()[0]).text())

    def manage(self):
        pass


class PackageInfoWidget(QTextEdit):
    def __init__(self, view):
        super(PackageInfoWidget, self).__init__()

        self.view = view

    def refresh(self, current, previous):
        # Get info of current package from the model's item
        info = self.view.model().itemFromIndex(current).info

        # Display info
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
