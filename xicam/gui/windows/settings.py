# Adapted from http://doc.qt.io/qt-5/qtwidgets-dialogs-configdialog-configdialog-cpp.html under BSD


# TODO QtModern, QtDarkStyle
# TODO Add remotes config
# TODO Add usage statistics config
# TODO QSettings

from qtpy.QtCore import *
from qtpy.QtGui import *
from qtpy.QtWidgets import *

from xicam.plugins import manager as pluginmanager


class ConfigDialog(QDialog):
    def __init__(self):
        super(ConfigDialog, self).__init__()

        # Set size and position
        self.setGeometry(0, 0, 900, 550)
        frameGm = self.frameGeometry()
        screen = QApplication.desktop().screenNumber(QApplication.desktop().cursor().pos())
        centerPoint = QApplication.desktop().screenGeometry(screen).center()
        frameGm.moveCenter(centerPoint)
        self.move(frameGm.topLeft())

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
        # mainLayout.addStretch(1)
        mainLayout.addSpacing(12)
        mainLayout.addWidget(self.buttonboxWidget)

        self.setLayout(mainLayout)
        self.setWindowTitle("Config Dialog")

        # Set modality
        self.setModal(True)

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
        try:
            for pluginInfo in pluginmanager.getPluginsOfCategory('SettingsPlugin'):
                pluginInfo.plugin_object.restore(QSettings().value(pluginInfo.name))
        except (AttributeError, TypeError, SystemError):
            # No settings saved
            pass
        self.apply()

    def ok(self):
        self._empty()
        self.apply()
        self.accept()

    def apply(self):
        for pluginInfo in pluginmanager.getPluginsOfCategory('SettingsPlugin'):
            QSettings().setValue(pluginInfo.name, pluginInfo.plugin_object.save())

    def close(self):
        self._empty()
        self.restore()
        self.reject()

    def _empty(self):
        """
        Disown all widget children (otherwise their c++ objects are force deleted when the dialog closes).
        Must be run in reverse to avoid index update errors
        """
        for i in reversed(range(self.pagesWidget.count())):
            self.pagesWidget.widget(i).setParent(None)

    def closeEvent(self, event):
        self.close()
        event.accept()

    def keyPressEvent(self, e: QKeyEvent):
        if e.key() != Qt.Key_Escape:
            super(ConfigDialog, self).keyPressEvent(e)
        else:
            self.close()
