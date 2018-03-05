from . import GUIPlugin, GUILayout
from pyqtgraph.parametertree import Parameter, ParameterTree
from qtpy.QtWidgets import *
from qtpy.QtGui import *


class _EZPlugin(GUIPlugin):
    def __init__(self, name, toolbuttons=None, parameters=None, appendheadertest=None,
                 centerwidget=None,
                 bottomwidget=None):
        self.name = name

        self.centerwidget = centerwidget() if callable(centerwidget) else centerwidget
        self.bottomwidget = bottomwidget() if callable(bottomwidget) else bottomwidget
        self.rightwidget = ParameterTree()
        self.toolbar = QToolBar()

        if parameters:
            self.parameters = Parameter(name='Params', type='group', children=parameters)
            self.rightwidget.setParameters(self.parameters, showTop=False)

        if toolbuttons:
            for toolbutton in toolbuttons:
                self.addToolButton(*toolbutton)

        if appendheadertest: self.appendHeader = appendheadertest

        self.stages = {'EZPlugin': GUILayout(self.centerwidget, right=self.rightwidget, bottom=self.bottomwidget,
                                             top=self.toolbar)}

        super(_EZPlugin, self).__init__()
        _EZPlugin.instance = self

    def setImage(self, data):
        self.centerwidget.setImage(data)

    def plot(self, *args, **kwargs):
        self.bottomwidget.plot(*args, **kwargs)

    def addParameter(self, **kwargs):
        self.rightwidget.addParameters(Parameter(**kwargs))

    def addToolButton(self, icon, method, text=None):
        tb = QAction(QIcon(icon), text, self.toolbar)
        tb.triggered.connect(method)
        self.toolbar.addAction(tb)


def EZPlugin(name='TestPlugin', toolbuttons=None, parameters=None, appendheadertest=None,
             centerwidget=None,
             bottomwidget=None):
    import pyqtgraph as pg
    if centerwidget is None: centerwidget = pg.ImageView
    if bottomwidget is None: bottomwidget = pg.PlotWidget
    return type(name, (_EZPlugin,), {'__init__': lambda self: _EZPlugin.__init__(self, name, toolbuttons, parameters,
                                                                                 appendheadertest, centerwidget,
                                                                                 bottomwidget),
                                     })
