from collections import OrderedDict

import qdarkstyle
from qtmodern import styles
from qtpy.QtGui import *
from qtpy.QtWidgets import QApplication
from xicam.gui.static import path
import pyqtgraph as pg

from xicam.plugins import ParameterSettingsPlugin


def setDefault():
    QApplication.instance().setStyleSheet("")


def setDark():
    QApplication.instance().setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())


def setModern():
    styles.dark(QApplication.instance())


def setUglyGreen():
    QApplication.instance().setStyleSheet("QWidget {background-color: darkgreen;}")


def setPlotWhite():
    pg.setConfigOption("background", "w")
    pg.setConfigOption("foreground", "k")


def setPlotDefault():
    pass


class AppearanceSettingsPlugin(ParameterSettingsPlugin):
    def __init__(self):
        super(AppearanceSettingsPlugin, self).__init__(
            QIcon(str(path("icons/colors.png"))),
            "Appearance",
            [
                dict(
                    name="Theme",
                    values=OrderedDict(
                        [
                            ("Default", setDefault),
                            ("QDarkStyle", setDark),
                            ("QtModern", setModern),
                            ("UglyGreen", setUglyGreen),
                        ]
                    ),
                    type="list",
                ),
                dict(
                    name="Plot Theme (requires restart)",
                    values=OrderedDict([("Default (Dark)", setPlotDefault), ("Publication (White)", setPlotWhite)]),
                    type="list",
                ),
            ],
        )

    def apply(self):
        self["Theme"]()
        self["Plot Theme (requires restart)"]()
