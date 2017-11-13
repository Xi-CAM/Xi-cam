from pyqtgraph.parametertree import ParameterTree, Parameter
from qtpy.QtGui import *
from qtpy.QtWidgets import *

from xicam.gui.static import path
from xicam.plugins import SettingsPlugin


class AppearanceSettingsPlugin(SettingsPlugin):
    def __init__(self):
        super(AppearanceSettingsPlugin, self).__init__(QIcon(str(path('icons/colors.png'))),
                                                       'Appearance')
        self.widget = AppearanceSettings()


class AppearanceSettings(ParameterTree):
    def __init__(self):
        super(AppearanceSettings, self).__init__(showHeader=False)
        settings = [dict(name='Theme',
                         value='Default',
                         values={'Default': 0,
                                 'QtDarkStyle': 1,
                                 'QtModern': 2},
                         type='list')]
        param = Parameter(name='Appearance', type='group', children=settings)
        self.setParameters(param, showTop=False)
