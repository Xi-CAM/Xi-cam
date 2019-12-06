from functools import partial
import sys

from qtpy.QtCore import QPropertyAnimation, QPoint, QEasingCurve, Qt, Slot, Signal, QSettings
from qtpy.QtGui import QIcon, QPixmap, QKeySequence, QFont
from qtpy.QtWidgets import QMainWindow, QApplication, QStatusBar, QProgressBar, QStackedWidget, QMenu, QShortcut, QDockWidget, QWidget, QToolBar, QActionGroup, QGraphicsOpacityEffect, QAction, QSpinBox
from xicam.plugins.guiplugin import PanelState
from yapsy import PluginInfo

from xicam.plugins import manager as pluginmanager
from xicam.plugins import EntryPointPluginInfo
from xicam.gui.widgets.debugmenubar import DebuggableMenuBar
from xicam.core import msg
from ..widgets import defaultstage
from .settings import ConfigDialog
from ..static import path
from databroker.core import BlueskyRun


class XicamMainWindow(QMainWindow):
    """
    The Xi-cam main window. Includes layout for various panels and mechanism to position GUIPlugin contents into panels.
    """

    def __init__(self):
        super(XicamMainWindow, self).__init__()

        # Set icon
        self.setWindowIcon(QIcon(QPixmap(str(path("icons/xicam.gif")))))

        # Set size and position
        self.setGeometry(0, 0, 1000, 600)
        frameGm = self.frameGeometry()
        screen = QApplication.desktop().screenNumber(QApplication.desktop().cursor().pos())
        centerPoint = QApplication.desktop().screenGeometry(screen).center()
        frameGm.moveCenter(centerPoint)
        self.move(frameGm.topLeft())

        # Init child widgets to None
        self.topwidget = (
            self.leftwidget
        ) = (
            self.rightwidget
        ) = (
            self.bottomwidget
        ) = self.lefttopwidget = self.righttopwidget = self.leftbottomwidget = self.rightbottomwidget = None

        # Setup appearance
        self.setWindowTitle("Xi-cam")

        # Load plugins
        pluginmanager.collectPlugins()

        # Restore Settings
        self._configdialog = ConfigDialog()
        self._configdialog.restore()

        # Setup center/toolbar/statusbar/progressbar
        self.pluginmodewidget = pluginModeWidget()
        self.pluginmodewidget.sigSetStage.connect(self.setStage)
        self.pluginmodewidget.sigSetGUIPlugin.connect(self.setGUIPlugin)
        self.addToolBar(self.pluginmodewidget)
        self.setStatusBar(QStatusBar(self))
        msg.progressbar = QProgressBar(self)
        msg.progressbar.hide()
        msg.statusbar = self.statusBar()
        self.statusBar().addPermanentWidget(msg.progressbar)
        self.setCentralWidget(QStackedWidget())
        # NOTE: CentralWidgets are force-deleted when replaced, even if the object is still referenced;
        # To avoid this, a QStackedWidget is used for the central widget.

        # Setup menubar
        menubar = DebuggableMenuBar()
        self.setMenuBar(menubar)
        file = QMenu("&File", parent=menubar)
        menubar.addMenu(file)
        file.addAction("Se&ttings", self.showSettings, shortcut=QKeySequence(Qt.CTRL + Qt.ALT + Qt.Key_S))
        file.addAction("E&xit", self.close)
        help = QMenu("&Help", parent=menubar)
        menubar.addMenu(help)

        # Initialize layout with first plugin
        self._currentGUIPlugin = None
        self.build_layout()

        # self._currentGUIPlugin = pluginmanager.getPluginsOfCategory("GUIPlugin")[0]
        self.populate_layout()

        # Make F key bindings
        fkeys = [
            Qt.Key_F1,
            Qt.Key_F2,
            Qt.Key_F3,
            Qt.Key_F4,
            Qt.Key_F5,
            Qt.Key_F6,
            Qt.Key_F7,
            Qt.Key_F8,
            Qt.Key_F9,
            Qt.Key_F10,
            Qt.Key_F11,
            Qt.Key_F12,
        ]
        self.Fshortcuts = [QShortcut(QKeySequence(key), self) for key in fkeys]
        for i in range(12):
            self.Fshortcuts[i].activated.connect(partial(self.setStage, i))


        self.readSettings()
        # Wireup default widgets
        defaultstage["left"].sigOpen.connect(self.open)
        defaultstage["left"].sigOpen.connect(print)
        defaultstage["left"].sigPreview.connect(defaultstage["lefttop"].preview_header)


    def open(self, header):
        if self.currentGUIPlugin is None:
            return
        if isinstance(header, (Catalog, CatalogEntry)):
            self.currentGUIPlugin.appendCatalog(header)
        else:
            self.currentGUIPlugin.appendHeader(header)

    def showSettings(self):
        self._configdialog.show()

    def setStage(self, stage):
        """
        Set the current Stage/Layout/Plugin mode to number i in its sequence. Triggered by menu (TODO) or F keybindings.

        Parameters
        ----------
        i   : int
        """
        plugin = self.currentGUIPlugin
        plugin.stage = stage
        self.populate_layout()

    def setGUIPlugin(self, guiplugin):
        self.currentGUIPlugin = guiplugin

    @property
    def currentGUIPlugin(self) -> PluginInfo:
        return self._currentGUIPlugin

    @currentGUIPlugin.setter
    def currentGUIPlugin(self, guiplugin):
        if guiplugin != self._currentGUIPlugin:
            self._currentGUIPlugin = guiplugin
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
        if self.currentGUIPlugin:
            stage = self.currentGUIPlugin.stage
        else:
            stage = defaultstage

        # Set center contents
        self.centralWidget().addWidget(stage.centerwidget)
        self.centralWidget().setCurrentWidget(stage.centerwidget)

        # Set visibility based on panel state and (TODO) insert default widgets when defaulted
        for position in ["top", "left", "right", "bottom", "lefttop", "righttop", "leftbottom", "rightbottom"]:
            self.populate_hidden(stage, position)
            self.populate_position(stage, position)

    def populate_hidden(self, stage, position):
        getattr(self, position + "widget").setHidden(
            (stage[position] == PanelState.Disabled)
            or (stage[position] == PanelState.Defaulted and defaultstage[position] == PanelState.Defaulted)
        )

    def populate_position(self, stage, position: str):
        if isinstance(stage[position], QWidget):
            getattr(self, position + "widget").setWidget(stage[position])
        elif stage[position] == PanelState.Defaulted:
            if not defaultstage[position] == PanelState.Defaulted:
                getattr(self, position + "widget").setWidget(defaultstage[position])
        elif isinstance(stage[position], type):
            raise TypeError(
                f"A type is not acceptable value for stages. You must instance this class: {stage[position]}, {position}"
            )

    def mousePressEvent(self, event):
        focused_widget = QApplication.focusWidget()
        if isinstance(focused_widget, QSpinBox):
            focused_widget.clearFocus()
        super(XicamMainWindow, self).mousePressEvent(event)

    def closeEvent(self, event):
        QSettings().setValue("geometry", self.saveGeometry())
        QMainWindow.closeEvent(self, event)

    def readSettings(self):
        settings = QSettings()
        if settings.value("geometry") is not None:
            self.restoreGeometry(settings.value("geometry"))


class Node(object):
    def __init__(self, object, name, children=None, parent=None):
        self.object = object
        self.name = name
        self.children = children or []
        self.parent = parent

class pluginModeWidget(QToolBar):
    """
    A series of styled QPushButtons with pipe characters between them. Used to switch between plugin modes.
    """

    sigSetStage = Signal(object)
    sigSetGUIPlugin = Signal(object)

    def __init__(self):
        super(pluginModeWidget, self).__init__()

        self.GUIPluginActionGroup = QActionGroup(self)

        # Setup font
        self.font = QFont("Zero Threes")
        self.font.setPointSize(16)

        # Align right
        self.setLayoutDirection(Qt.RightToLeft)

        # Subscribe to plugins
        pluginmanager.attach(self.pluginsChanged)

        self._nodes = []

        # Build children
        self.pluginsChanged()

    def _build_nodes(self):
        self._nodes = []
        for plugin in pluginmanager.getPluginsOfCategory("GUIPlugin"):

            node = Node(plugin, plugin.plugin_object.name)

            for name, stage in plugin.plugin_object.stages.items():
                node.children.append(self._build_subnodes(name, stage, parent=node))

            self._nodes.append(node)

    def _build_subnodes(self, name, stage, parent):
        node = Node(stage, name, parent=parent)
        if isinstance(stage, dict):
            for subname, substage in stage.items():
                node.children.append(self._build_subnodes(subname, substage, parent=node))

        self._nodes.append(node)

        return node


    def pluginsChanged(self):
        self._build_nodes()
        self.showNode()

    def showNode(self, node=None, direction=None):
        if node is None:  # toplevel
            plugin_nodes = [node for node in self._nodes if node.parent is None]
            # TODO: add plugin deactivation
            nodes = [node for node in plugin_nodes if getattr(node.object, "is_activated", True) or True]
            self._showNodes(nodes, direction)
            # self.fadeOut(callback=partial(self.mkButtons, names=names, callback=self.showStages), distance=0)

        elif isinstance(node.object, (dict, PluginInfo.PluginInfo, EntryPointPluginInfo)):
            nodes = node.children
            if len(nodes) > 1:
                self._showNodes(nodes, direction)
            self.sigSetGUIPlugin.emit(node.object.plugin_object)
            self.setStage(node.object.plugin_object.stage)

        # elif isinstance(node.object, dict): # midlevel
        #     self._showNodes(node.object.keys(), node.object.values(), direction)

        else:  # bottomlevel
            parent_node = node.parent
            while parent_node.parent is not None:
                parent_node = parent_node.parent
            self.sigSetGUIPlugin.emit(parent_node.object.plugin_object)
            self.setStage(node.object)

            # self.fadeOut(callback=partial(self.mkButtons, names=names, callback=self.showStages), distance=0)

    def _showNodes(self, nodes, direction=None):
        if direction == 'up':
            distance = 20
        elif direction == 'down':
            distance = -20
        else:
            distance = 0

        self.fadeOut(callback=partial(self.mkButtons, nodes=nodes), distance=distance)

    def fadeOut(self, callback, distance=-20):
        duration = 200
        self._effects = []
        for action in self.actions():
            for widget in action.associatedWidgets():
                if widget is not self:
                    a = QPropertyAnimation(widget, b"pos", widget)
                    a.setStartValue(widget.pos())
                    a.setEndValue(widget.pos() + QPoint(0, distance))
                    self._effects.append(a)
                    a.setDuration(duration)
                    a.setEasingCurve(QEasingCurve.OutBack)
                    a.start(QPropertyAnimation.DeleteWhenStopped)

                    effect = QGraphicsOpacityEffect(self)
                    widget.setGraphicsEffect(effect)
                    self._effects.append(effect)
                    b = QPropertyAnimation(effect, b"opacity")
                    self._effects.append(b)
                    b.setDuration(duration)
                    b.setStartValue(1)
                    b.setEndValue(0)
                    b.setEasingCurve(QEasingCurve.OutBack)
                    b.start(QPropertyAnimation.DeleteWhenStopped)
                    b.finished.connect(partial(self.removeAction, action))
                    b.finished.connect(callback)
        if not self.actions():
            callback()

    def fadeIn(self):
        self._effects = []
        for action in self.actions():
            effect = QGraphicsOpacityEffect(self)
            self._effects.append(effect)
            for widget in action.associatedWidgets():
                if widget is not self:
                    widget.setGraphicsEffect(effect)
            a = QPropertyAnimation(effect, b"opacity")
            self._effects.append(a)
            a.setDuration(1000)
            a.setStartValue(0)
            a.setEndValue(1)
            a.setEasingCurve(QEasingCurve.OutBack)
            a.start(QPropertyAnimation.DeleteWhenStopped)

    # def showStages(self, plugin, *, parent_stage=None):
    #     if not parent_stage:
    #         self.sigSetGUIPlugin.emit(plugin)
    #     if len(self.parent().currentGUIPlugin.plugin_object.stages) > 1:
    #         if parent_stage:
    #             names = self.parent().currentGUIPlugin.plugin_object.stages[parent_stage].keys()
    #         else:
    #             names = self.parent().currentGUIPlugin.plugin_object.stages.keys()
    #
    #         parent = self.parent().currentGUIPlugin.plugin_object.name
    #         if parent_stage:
    #             parent += f' > {parent_stage}'
    #
    #         self.fadeOut(
    #             callback=partial(
    #                 self.mkButtons,
    #                 names=names,
    #                 callback=self.setStage,#self.sigSetStage.emit,
    #                 parent=parent,
    #             )
    #         )

    def setStage(self, stage):
        self.sigSetStage.emit(stage)
        # if isinstance(list(self.parent().currentGUIPlugin.plugin_object.stages.values())[i], dict):
        #     self.showStages(self.parent().currentGUIPlugin.plugin_object, parent_stage=list(self.parent().currentGUIPlugin.plugin_object.stages.keys())[i])

    # def showGUIPlugins(self, distance=20):
    #     plugins = pluginmanager.getPluginsOfCategory("GUIPlugin")
    #     # TODO: test deactivated plugins
    #     names = [
    #         plugin.plugin_object.name for plugin in plugins if getattr(plugin, "is_activated", True) or True
    #     ]  # TODO: add plugin deactivation
    #     self.fadeOut(callback=partial(self.mkButtons, names=names, callback=self.showStages), distance=distance)

    def mkButtons(self, nodes):
        # Remove+delete previous children
        layout = self.layout()
        for i in reversed(range(layout.count())):
            layout.itemAt(i).widget().setParent(None)

        if not nodes: return

        parent = nodes[0].parent

        if parent is not None:
            action = QAction("↑", self)
            action.setFont(self.font)
            action.triggered.connect(partial(self.showNode, parent.parent, direction='up'))
            action.setProperty("isMode", True)
            self.addAction(action)
            # Make separator pipe
            label = QAction("|", self)
            label.setFont(self.font)
            label.setDisabled(True)
            self.addAction(label)

        # Loop over each "GUIPlugin" plugin
        for node in reversed(list(nodes)):
            action = QAction(node.name, self)
            action.triggered.connect(partial(self.showNode, node, direction='down'))
            action.setFont(self.font)
            action.setProperty("isMode", True)
            action.setCheckable(True)
            action.setActionGroup(self.GUIPluginActionGroup)
            self.addAction(action)

            # Make separator pipe
            label = QAction("|", self)
            label.setFont(self.font)
            label.setDisabled(True)
            self.addAction(label)

        # Remove last separator
        if self.layout().count():
            self.layout().takeAt(self.layout().count() - 1).widget().deleteLater()  # Delete the last pipe symbol

        if parent is not None:
            # Make separator pipe
            label = QAction(">", self)
            label.setFont(self.font)
            label.setDisabled(True)
            self.addAction(label)

            action = QAction(parent.name, self)
            action.setFont(self.font)
            action.setProperty("isMode", True)
            action.setDisabled(True)
            action.setActionGroup(self.GUIPluginActionGroup)
            self.addAction(action)

        self.fadeIn()
