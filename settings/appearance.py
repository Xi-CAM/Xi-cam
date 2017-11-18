from qtpy.QtWidgets import *

from xicam.gui.static import path
from xicam.plugins import SettingsPlugin

AppearanceSettingsPlugin = SettingsPlugin.fromParameter(QIcon(str(path('icons/colors.png'))),
                                                        'Appearance',
                                                        [dict(name='Theme',
                                                              value='Default',
                                                              values={'Default': 0,
                                                                      'QtDarkStyle': 1,
                                                                      'QtModern': 2},
                                                              type='list')]
                                                        )
