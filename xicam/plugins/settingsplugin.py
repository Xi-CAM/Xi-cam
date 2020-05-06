from typing import List
from qtpy.QtCore import QObject, QSettings
from .plugin import PluginType
from xicam import plugins
from pyqtgraph.parametertree import ParameterTree
from pyqtgraph.parametertree.parameterTypes import GroupParameter
import cloudpickle as pickle
from xicam.core import msg


class SettingsPlugin(QObject, PluginType):
    is_singleton = True
    needs_qt = False

    def __init__(self, icon, name, widget):
        super(SettingsPlugin, self).__init__()
        self.icon = icon
        self._name = name
        self._widget = widget

    @property
    def widget(self):
        return self._widget

    @widget.setter
    def widget(self, widget):
        self._widget = widget

    def name(self):
        return self._name

    def apply(self):
        ...

    def toState(self):
        self.apply()
        ...

    def fromState(self, state):
        ...

    def save(self):
        QSettings().setValue(self.name(), pickle.dumps(self.toState()))

    def restore(self):
        try:
            state = QSettings().value(self.name())
            if state != pickle.dumps(self.toState()):
                self.fromState(pickle.loads(state))
            # else:
            #     msg.logMessage(f"skipped restoring {self.name()}")
        except (AttributeError, TypeError, SystemError, KeyError, ModuleNotFoundError) as ex:
            # No settings saved
            msg.logError(ex)
            msg.logMessage(
                f"Could not restore settings for {self.name} plugin; re-initializing settings...", level=msg.WARNING
            )


class ParameterSettingsPlugin(GroupParameter, SettingsPlugin):
    def __init__(self, icon, name: str, paramdicts: List[dict], **kwargs):
        SettingsPlugin.__init__(self, icon, name, None)
        GroupParameter.__init__(self, name=name, type="group", children=paramdicts, **kwargs)
        self.restore()

    @property
    def widget(self):
        widget = ParameterTree()
        widget.setParameters(self, showTop=False)
        return widget

    def apply(self):
        pass

    def toState(self):
        self.apply()
        return self.saveState(filter="user")

    def fromState(self, state):
        self.restoreState(state, addChildren=False, removeChildren=False)
