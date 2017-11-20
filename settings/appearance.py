from qtpy.QtGui import *
from xicam.gui.static import path
from xicam.plugins import SettingsPlugin
from qtpy.QtWidgets import QApplication
import qdarkstyle
from qtmodern import styles
from collections import OrderedDict
from collections import OrderedDict

import qdarkstyle
from qtmodern import styles
from qtpy.QtGui import *
from qtpy.QtWidgets import QApplication

from xicam.gui.static import path
from xicam.plugins import SettingsPlugin


def setDefault():
    QApplication.instance().setStyleSheet("")


def setDark():
    QApplication.instance().setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())


def setModern():
    styles.dark(QApplication.instance())

AppearanceSettingsPlugin = SettingsPlugin.fromParameter(QIcon(str(path('icons/colors.png'))),
                                                        'Appearance',
                                                        [dict(name='Theme',
                                                              values=OrderedDict([('Default', setDefault),
                                                                                  ('QDarkStyle', setDark),
                                                                                  ('QtModern', setModern)]),
                                                              type='list')]
                                                        )


def apply(self):
    self.parameter['Theme']()


AppearanceSettingsPlugin.apply = apply
