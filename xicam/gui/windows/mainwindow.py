from functools import partial

from qtpy.QtCore import *
from qtpy.QtGui import *
from qtpy.QtWidgets import *
from xicam.plugins.GUIPlugin import PanelState
from yapsy import PluginInfo

from xicam.plugins import manager as pluginmanager
from xicam.plugins import observers as pluginobservers
from ..widgets import defaultstage
from .settings import ConfigDialog


class XicamMainWindow(QMainWindow):
    """
    The Xi-cam main window. Includes layout for various panels and mechanism to position GUIPlugin contents into panels.
    """

    def __init__(self):
        super(XicamMainWindow, self).__init__()

        # Set size and position
        self.setGeometry(0, 0, 1000, 600)
        frameGm = self.frameGeometry()
        screen = QApplication.desktop().screenNumber(QApplication.desktop().cursor().pos())
        centerPoint = QApplication.desktop().screenGeometry(screen).center()
        frameGm.moveCenter(centerPoint)
        self.move(frameGm.topLeft())

        # Init child widgets to None
        self.topwidget = self.leftwidget = self.rightwidget = self.bottomwidget = self.lefttopwidget = \
            self.righttopwidget = self.leftbottomwidget = self.rightbottomwidget = None

        # Setup appearance
        self.setWindowTitle('Xi-cam')

        # Restore Settings
        ConfigDialog().restore()

        # Load GUIPlugins
        pluginmanager.instanciateLatePlugins()

        # Setup center/toolbar/statusbar
        pluginmodewidget = pluginModeWidget()
        pluginmodewidget.sigSetStage.connect(self.setStage)
        self.addToolBar(pluginmodewidget)
        self.setStatusBar(QStatusBar())
        self.setCentralWidget(QStackedWidget())
        # NOTE: CentralWidgets are force-deleted when replaced, even if the object is still referenced;
        # To avoid this, a QStackedWidget is used for the central widget.

        # Setup menubar
        menubar = self.menuBar()
        file = QMenu('&File', parent=menubar)
        menubar.addMenu(file)
        file.addAction('Se&ttings', self.showSettings, shortcut=QKeySequence(Qt.CTRL + Qt.ALT + Qt.Key_S))
        file.addAction('E&xit', self.close)
        help = QMenu('&Help', parent=menubar)
        menubar.addMenu(help)

        # Initialize layout with first plugin
        self._currentGUIPlugin = None
        self.build_layout()
        if pluginmanager.getPluginsOfCategory("GUIPlugin"):
            self._currentGUIPlugin = pluginmanager.getPluginsOfCategory("GUIPlugin")[0]
            self.populate_layout()

        # Make F key bindings
        fkeys = [Qt.Key_F1, Qt.Key_F2, Qt.Key_F3, Qt.Key_F4, Qt.Key_F5, Qt.Key_F6,
                 Qt.Key_F7, Qt.Key_F8, Qt.Key_F9, Qt.Key_F10, Qt.Key_F11, Qt.Key_F12]
        self.Fshortcuts = [QShortcut(QKeySequence(key), self) for key in fkeys]
        for i in range(12):
            self.Fshortcuts[i].activated.connect(partial(self.setStage, i))

        # Wireup default widgets
        defaultstage['left'].sigOpen.connect(self.open)
        defaultstage['left'].sigOpen.connect(print)
        defaultstage['left'].sigPreview.connect(defaultstage['lefttop'].preview_header)

    def open(self, header):
        print(header)
        self.currentGUIPlugin.plugin_object.appendHeader(header)

    def showSettings(self):
        self._configdialog = ConfigDialog()
        self._configdialog.show()

    @Slot(int)
    def setStage(self, i: int):
        """
        Set the current Stage/Layout/Plugin mode to number i in its sequence. Triggered by menu (TODO) or F keybindings.

        Parameters
        ----------
        i   : int
        """
        plugin = self.currentGUIPlugin.plugin_object
        if i < len(plugin.stages):
            plugin.stage = list(plugin.stages.values())[i]
            self.populate_layout()

    @property
    def currentGUIPlugin(self) -> PluginInfo:
        return self._currentGUIPlugin

    @currentGUIPlugin.setter
    def currentGUIPlugin(self, plugininfo: PluginInfo):
        if plugininfo != self._currentGUIPlugin:
            self._currentGUIPlugin = plugininfo
            self.populate_layout()

    def build_layout(self):
        # TODO: Allow save/restore https://stackoverflow.com/questions/14288635/any-easy-way-to-store-dock-widows-layout-and-sizes-in-settings-with-qt

        # Clear out docks
        for dockwidget in self.findChildren(QDockWidget):
            if dockwidget.parent() == self:
                self.removeDockWidget(dockwidget)

        # Make new docks
        self.topwidget = QDockWidget(parent=self)
        self.leftwidget = QDockWidget(parent=self)
        self.rightwidget = QDockWidget(parent=self)
        self.bottomwidget = QDockWidget(parent=self)
        self.lefttopwidget = QDockWidget(parent=self)
        self.righttopwidget = QDockWidget(parent=self)
        self.leftbottomwidget = QDockWidget(parent=self)
        self.rightbottomwidget = QDockWidget(parent=self)

        # Place the docks
        self.addDockWidget(Qt.LeftDockWidgetArea, self.lefttopwidget)
        self.addDockWidget(Qt.RightDockWidgetArea, self.righttopwidget)
        self.addDockWidget(Qt.TopDockWidgetArea, self.topwidget)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.leftwidget)
        self.addDockWidget(Qt.RightDockWidgetArea, self.rightwidget)
        self.addDockWidget(Qt.BottomDockWidgetArea, self.bottomwidget)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.leftbottomwidget)
        self.addDockWidget(Qt.RightDockWidgetArea, self.rightbottomwidget)

        # Adjust spanning
        self.setCorner(Qt.TopLeftCorner, Qt.LeftDockWidgetArea)
        self.setCorner(Qt.TopRightCorner, Qt.RightDockWidgetArea)
        self.setCorner(Qt.BottomLeftCorner, Qt.LeftDockWidgetArea)
        self.setCorner(Qt.BottomRightCorner, Qt.RightDockWidgetArea)

    def populate_layout(self):
        # Get current stage
        stage = self.currentGUIPlugin.plugin_object.stage

        # Set center contents
        self.centralWidget().addWidget(stage.centerwidget)
        self.centralWidget().setCurrentWidget(stage.centerwidget)

        # Set visibility based on panel state and (TODO) insert default widgets when defaulted
        for position in ['top','left','right','bottom','lefttop','righttop','leftbottom','rightbottom']:
            self.populate_hidden(stage, position)
            self.populate_position(stage, position)

    def populate_hidden(self, stage, position):
        getattr(self,position+'widget').setHidden((stage[position] == PanelState.Disabled) or
                                                  (stage[position] == PanelState.Defaulted and
                                                   defaultstage[position] == PanelState.Defaulted))

    def populate_position(self, stage, position:str):
        if isinstance(stage[position], QWidget):
            getattr(self,position+'widget').setWidget(stage[position])
        elif stage[position] == PanelState.Defaulted:
            if not defaultstage[position]==PanelState.Defaulted:
                getattr(self,position+'widget').setWidget(defaultstage[position])

class pluginModeWidget(QToolBar):
    """
    A series of styled QPushButtons with pipe characters between them. Used to switch between plugin modes.
    """
    sigSetStage = Signal(int)

    def __init__(self):
        super(pluginModeWidget, self).__init__()

        # Setup font
        self.font = QFont()
        self.font.setPointSize(16)

        # Align right
        self.setLayoutDirection(Qt.RightToLeft)

        # Subscribe to plugins
        pluginobservers.append(self)

        # Build children
        self.pluginsChanged()

    def pluginsChanged(self):
        # Remove+delete previous children
        layout = self.layout()
        for i in reversed(range(layout.count())):
            layout.itemAt(i).widget().setParent(None)

        # Loop over each "GUIPlugin" plugin
        for plugin in pluginmanager.getPluginsOfCategory("GUIPlugin"):
            if plugin.is_activated or True:
                # Make the pushbutton
                button = HoverMenuButton(stages=plugin.plugin_object.stages, text=plugin.name)
                button.setFlat(True)
                button.setFont(self.font)
                button.setProperty('isMode', True)
                button.setAutoFillBackground(False)
                button.setCheckable(True)
                button.setAutoExclusive(True)
                button.sigSetStage.connect(self.sigSetStage)
                self.addWidget(button)

                # Connect pushbutton
                button.clicked.connect(partial(self.activate, plugin))
                # if plugin is self.plugins.values()[0]:
                #     button.setChecked(True)

                # Make separator pipe
                label = QLabel('|')
                label.setFont(self.font)
                # label.setStyleSheet('background-color:#111111;')
                self.addWidget(label)

        # Remove last separator
        if self.layout().count():
            self.layout().takeAt(self.layout().count() - 1).widget().deleteLater()  # Delete the last pipe symbol

    def activate(self, plugin):
        # Set the current plugin (automatically replaces layout)
        self.parent().currentGUIPlugin = plugin


class HoverMenuButton(QPushButton):
    sigSetGUIPlugin = Signal()
    sigSetStage = Signal(int)

    def __init__(self, stages, *args, **kwargs):
        super(HoverMenuButton, self).__init__(*args, **kwargs)
        if len(stages) > 1:
            menu = QMenu()
            for i, name in enumerate(stages.keys()):
                menu.addAction(name, partial(self.menuClicked, i))
            menu.leaveEvent = self.leaveEvent
            self.setMenu(menu)

    def menuClicked(self, stage):
        self.clicked.emit()
        self.setChecked(True)
        self.sigSetStage.emit(stage)

    def enterEvent(self, event):
        if self.menu():
            self.showMenu()

    def leaveEvent(self, *args, **kwargs):
        if self.menu():
            self.menu().hide()
