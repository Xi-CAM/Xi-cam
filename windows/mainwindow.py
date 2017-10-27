from functools import partial

from qtpy.QtCore import *
from qtpy.QtGui import *
from qtpy.QtWidgets import *
from yapsy import PluginInfo

from xicam.plugins import manager


class XicamMainWindow(QMainWindow):
    def __init__(self):
        super(XicamMainWindow, self).__init__()

        # Init starting widgets
        self.topwidget = self.leftwidget = self.rightwidget = self.bottomwidget = self.topleftwidget = \
            self.toprightwidget = self.bottomleftwidget = self.bottomrightwidget = None
        # Setup center/toolbar/statusbar
        self.addToolBar(pluginModeWidget())
        self.setStatusBar(QStatusBar())
        self.setCentralWidget(QStackedWidget())

        # NOTE: CentralWidgets are force-deleted when replaced, even if the object is still referenced;
        # To avoid this, a QStackedWidget is used for the central widget.

        # Initialize layout
        self._currentGUIPlugin = manager.getPluginsOfCategory("GUIPlugin")[0]
        self.rebuild_layout()

        fkeys = [Qt.Key_F1, Qt.Key_F2, Qt.Key_F3, Qt.Key_F4, Qt.Key_F5, Qt.Key_F6,
                 Qt.Key_F7, Qt.Key_F8, Qt.Key_F9, Qt.Key_F10, Qt.Key_F11, Qt.Key_F12]
        self.Fshortcuts = [QShortcut(QKeySequence(key), self) for key in fkeys]
        for i in range(12):
            self.Fshortcuts[i].activated.connect(partial(self.setStage, i))

    def setStage(self, i):
        plugin = self.currentGUIPlugin.plugin_object
        plugin.stage = list(plugin.stages.values())[i]
        self.rebuild_layout()

    @property
    def currentGUIPlugin(self) -> PluginInfo:
        return self._currentGUIPlugin

    @currentGUIPlugin.setter
    def currentGUIPlugin(self, plugininfo: PluginInfo):
        self._currentGUIPlugin = plugininfo

    def rebuild_layout(self):
        # TODO: Allow save/restore https://stackoverflow.com/questions/14288635/any-easy-way-to-store-dock-widows-layout-and-sizes-in-settings-with-qt

        # Clear out docks
        for dockwidget in self.findChildren(QDockWidget):
            if dockwidget.parent() == self:
                self.removeDockWidget(dockwidget)

        # Make new docks
        self.topwidget = QDockWidget('top', parent=self)
        self.leftwidget = QDockWidget('left', parent=self)
        self.rightwidget = QDockWidget('right', parent=self)
        self.bottomwidget = QDockWidget('bottom', parent=self)
        self.topleftwidget = QDockWidget('topleft', parent=self)
        self.toprightwidget = QDockWidget('topright', parent=self)
        self.bottomleftwidget = QDockWidget('bottomleft', parent=self)
        self.bottomrightwidget = QDockWidget('bottomright', parent=self)

        # Place the docks
        self.addDockWidget(Qt.TopDockWidgetArea, self.topwidget)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.leftwidget)
        self.addDockWidget(Qt.RightDockWidgetArea, self.rightwidget)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.topleftwidget)
        self.addDockWidget(Qt.BottomDockWidgetArea, self.bottomwidget)
        self.addDockWidget(Qt.RightDockWidgetArea, self.toprightwidget)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.bottomleftwidget)
        self.addDockWidget(Qt.RightDockWidgetArea, self.bottomrightwidget)

        # Adjust spanning
        self.setCorner(Qt.TopLeftCorner, Qt.LeftDockWidgetArea)
        self.setCorner(Qt.TopRightCorner, Qt.RightDockWidgetArea)
        self.setCorner(Qt.BottomLeftCorner, Qt.LeftDockWidgetArea)
        self.setCorner(Qt.BottomRightCorner, Qt.RightDockWidgetArea)

        self.centralWidget().addWidget(self.currentGUIPlugin.plugin_object.stage.centerwidget)
        self.centralWidget().setCurrentWidget(self.currentGUIPlugin.plugin_object.stage.centerwidget)


class pluginModeWidget(QToolBar):
    def __init__(self):
        super(pluginModeWidget, self).__init__()

        self.font = QFont()
        self.font.setPointSize(16)

        self.setLayoutDirection(Qt.RightToLeft)

        self.reload()

    def reload(self):

        # Loop over each "GUIPlugin" plugin
        for plugin in manager.getPluginsOfCategory("GUIPlugin"):
            print(plugin)
            if plugin.is_activated or True:
                button = QPushButton(plugin.name)
                button.setFlat(True)
                button.setFont(self.font)
                button.setProperty('isMode', True)
                button.setAutoFillBackground(False)
                button.setCheckable(True)
                button.setAutoExclusive(True)
                # button.clicked.connect(plugin.activate)
                # if plugin is self.plugins.values()[0]:
                #     button.setChecked(True)
                self.addWidget(button)
                label = QLabel('|')
                label.setFont(self.font)
                # label.setStyleSheet('background-color:#111111;')
                self.addWidget(label)

        self.layout().takeAt(self.layout().count() - 1).widget().deleteLater()  # Delete the last pipe symbol
