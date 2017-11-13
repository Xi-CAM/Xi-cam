# Adapted from http://doc.qt.io/qt-5/qtwidgets-dialogs-configdialog-configdialog-cpp.html under BSD


# TODO QtModern, QtDarkStyle

from qtpy.QtGui import *
from qtpy.QtWidgets import *

from xicam.plugins import manager as pluginmanager
from xicam.plugins import observers as pluginobservers


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
        self.buttonboxWidget.button(QDialogButtonBox.apply).clicked.connect(self.apply)
        self.buttonboxWidget.button(QDialogButtonBox.close).clicked.connect(self.close)

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
        pluginobservers.append(self)

    def createIcons(self):
        for pluginInfo in pluginmanager.getPluginsOfCategory('SettingsPlugin'):
            self.contentsModel.appendRow(pluginInfo.plugin_object)

    def changePage(self, current, previous):
        if not current:
            current = previous
        current = self.contentsModel.itemFromIndex(current)
        self.pagesWidget.addWidget(current.widget)
        self.pagesWidget.setCurrentWidget(current.widget)

    def pluginsChanged(self):
        self.createIcons()

    def ok(self):
        self.accept()

    def apply(self):
        for pluginInfo in pluginmanager.getPluginsOfCategory('SettingsPlugin'):
            pluginInfo.plugin_object.save()

    def close(self):
        self.reject()
