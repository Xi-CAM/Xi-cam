from pyqtgraph.parametertree import ParameterTree, Parameter
from qtpy.QtGui import *
from qtpy.QtWidgets import *

from xicam.gui.static import path
from xicam.plugins import SettingsPlugin


class AppearanceSettingsPlugin(SettingsPlugin):
    name = "Appearance"

    def __init__(self):
        self.widget = ParameterTree()
        super(AppearanceSettingsPlugin, self).__init__(QIcon(str(path('icons/colors.png'))),
                                                       self.name,
                                                       self.widget)
        self.parameter = AppearanceSettings()
        self.widget.setParameters(self.parameter, showTop=False)

    def save(self):
        return self.parameter.saveState()

    def restore(self, state):
        self.parameter.restoreState(state)




class AppearanceSettings(Parameter):
    def __init__(self):
        settings = [dict(name='Theme',
                         value='Default',
                         values={'Default': 0,
                                 'QtDarkStyle': 1,
                                 'QtModern': 2},
                         type='list')]
        super(AppearanceSettings, self).__init__(name='Appearance', type='group', children=settings)


