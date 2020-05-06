# Adapted from http://doc.qt.io/qt-5/qtwidgets-dialogs-configdialog-configdialog-cpp.html under BSD


# TODO Add remotes config
# TODO Add usage statistics config

from qtpy.QtCore import Qt, QSize
from qtpy.QtGui import QStandardItemModel, QStandardItem, QKeyEvent
from qtpy.QtWidgets import (
    QDialog,
    QApplication,
    QListView,
    QStackedWidget,
    QHBoxLayout,
    QVBoxLayout,
    QAbstractItemView,
    QDialogButtonBox,
)

from xicam.plugins import manager as pluginmanager, Filters
from xicam.core import msg


class ConfigRestorer:
    def __init__(self):
        # Restore Settings
        pluginmanager.attach(self.request_reload, Filters.COMPLETE)

    @staticmethod
    def request_reload():
        for plugin in pluginmanager.get_plugins_of_type("SettingsPlugin"):
            plugin.restore()
            plugin.save()


class ConfigDialog(QDialog):
    def __init__(self):
        super(ConfigDialog, self).__init__()

        self.needs_reload = True

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
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel | QDialogButtonBox.Apply  # | QDialogButtonBox.Help
        )
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

        self.lastwidget = None

        # Restore Settings
        pluginmanager.attach(self.request_reload, Filters.COMPLETE)

    def request_reload(self):
        if self.isVisible():
            self.reload()
        else:
            self.needs_reload = True  # The restore will happen when shown

    def createIcons(self):
        self.contentsModel.clear()
        for plugin in pluginmanager.get_plugins_of_type("SettingsPlugin"):
            item = QStandardItem(plugin.icon, plugin.name())
            item.widget = plugin.widget
            item.setTextAlignment(Qt.AlignHCenter)
            item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
            item.setSizeHint(QSize(136, 80))
            self.contentsModel.appendRow(item)

    def show(self):
        if self.lastwidget:
            self.pagesWidget.addWidget(self.lastwidget)
            self.pagesWidget.setCurrentWidget(self.lastwidget)
        if self.needs_reload:
            self.reload()
        super(ConfigDialog, self).show()

    def changePage(self, current, previous):
        if not current:
            current = previous
        current = self.contentsModel.itemFromIndex(current)
        self.pagesWidget.addWidget(current.widget)
        self.pagesWidget.setCurrentWidget(current.widget)
        self.lastwidget = current.widget

    def reload(self):
        self.createIcons()

    def ok(self):
        self._empty()
        self.apply()
        self.accept()

    def apply(self):
        for plugin in pluginmanager.get_plugins_of_type("SettingsPlugin"):
            plugin.save()

    def close(self):
        self._empty()
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
