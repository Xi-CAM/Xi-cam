from typing import List
from qtpy.QtCore import QObject
from yapsy.IPlugin import IPlugin
from xicam import plugins


class SettingsPlugin(QObject, IPlugin):
    def __new__(cls, *args, **kwargs):
        if not plugins.qt_is_safe: return None
        return super(SettingsPlugin, cls).__new__(cls, *args, **kwargs)

    def __init__(self, icon, name, widget):
        super(SettingsPlugin, self).__init__()
        self.icon = icon
        self.name = name
        self.widget = widget

    @staticmethod
    def fromParameter(icon, name: str, paramdicts: List[dict]):
        if not plugins.qt_is_safe: return None
        from pyqtgraph.parametertree import Parameter, ParameterTree
        widget = ParameterTree()
        parameter = Parameter(name=name, type='group', children=paramdicts)
        widget.setParameters(parameter, showTop=False)

        def __init__(self):
            SettingsPlugin.__init__(self, icon, name, widget)

        return type(name + 'SettingsPlugin', (SettingsPlugin,), {'__init__': __init__, 'parameter': parameter})

    def apply(self):
        raise NotImplementedError

    def save(self):
        self.apply()
        return self.parameter.saveState(filter='user')

    def restore(self, state):
        self.parameter.restoreState(state, addChildren=False, removeChildren=False)
