# Adapted from http://doc.qt.io/qt-5/qtwidgets-dialogs-configdialog-configdialog-cpp.html under BSD


# TODO QtModern, QtDarkStyle
# TODO QSettings

from qtpy.QtGui import *
from qtpy.QtCore import *
from qtpy.QtWidgets import *

from xicam.plugins import manager as pluginmanager
from xicam.plugins import observers as pluginobservers
import yaml
from appdirs import user_config_dir, site_config_dir
from pathlib import Path

user_settings_dir = user_config_dir('xicam/settings')
site_settings_dir = site_config_dir('xicam/settings')

class ConfigDialog(QDialog):
    def __init__(self):
        super(ConfigDialog, self).__init__()

        self.contentsWidget = QListView()
        self.contentsWidget.setViewMode(QListView.IconMode)
        # self.contentsWidget.setIconSize(QSize(96, 84))
        self.contentsWidget.setMovement(QListView.Static)
        self.contentsWidget.setMaximumWidth(174)
        self.contentsWidget.setSpacing(12)
        self.contentsWidget.setSelectionMode(QAbstractItemView.SingleSelection)

        self.contentsModel = QStandardItemModel()
        self.contentsWidget.setModel(self.contentsModel)
        self.contentsWidget.selectionModel().currentChanged.connect(self.changePage)

        self.buttonboxWidget = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel | QDialogButtonBox.Apply | QDialogButtonBox.Help)
        self.buttonboxWidget.button(QDialogButtonBox.Ok).clicked.connect(self.ok)
        self.buttonboxWidget.button(QDialogButtonBox.Apply).clicked.connect(self.apply)
        self.buttonboxWidget.button(QDialogButtonBox.Cancel).clicked.connect(self.close)

        self.pagesWidget = QStackedWidget()

        horizontalLayout = QHBoxLayout()
        horizontalLayout.addWidget(self.contentsWidget)
        horizontalLayout.addWidget(self.pagesWidget, 1)

        mainLayout = QVBoxLayout()
        mainLayout.addLayout(horizontalLayout)
        mainLayout.addStretch(1)
        mainLayout.addSpacing(12)
        mainLayout.addWidget(self.buttonboxWidget)

        self.setLayout(mainLayout)
        self.setWindowTitle("Config Dialog")

        self.createIcons()
        self.restore()

    def createIcons(self):
        for pluginInfo in pluginmanager.getPluginsOfCategory('SettingsPlugin'):
            item = QStandardItem(pluginInfo.plugin_object.icon, pluginInfo.plugin_object.name)
            item.widget = pluginInfo.plugin_object.widget
            item.setTextAlignment(Qt.AlignHCenter)
            item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
            item.setSizeHint(QSize(136, 80))
            self.contentsModel.appendRow(item)

    def changePage(self, current, previous):
        if not current:
            current = previous
        current = self.contentsModel.itemFromIndex(current)
        self.pagesWidget.addWidget(current.widget)
        self.pagesWidget.setCurrentWidget(current.widget)

    def pluginsChanged(self):
        self.createIcons()

    def restore(self):
        for pluginInfo in pluginmanager.getPluginsOfCategory('SettingsPlugin'):
            path = Path(user_settings_dir, pluginInfo.name+'.yml')
            if path.is_file():
                with open(path, 'r') as infile:
                    pluginInfo.plugin_object.restore(yaml.load(infile))

    def ok(self):
        self._empty()
        self.apply()
        self.accept()

    def apply(self):
        for pluginInfo in pluginmanager.getPluginsOfCategory('SettingsPlugin'):
            path = Path(user_settings_dir, pluginInfo.name+'.yml')
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, 'w') as outfile:
                yaml.dump(pluginInfo.plugin_object.save(), outfile)

    def close(self):
        self._empty()
        self.restore()
        self.reject()

    def _empty(self):
        """
        Disown all widget children (otherwise their c++ objects are force deleted when the dialog closes).
        """
        for i in range(self.pagesWidget.count()):
            self.pagesWidget.widget(i).setParent(None)
