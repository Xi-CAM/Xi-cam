from . import GUIPlugin, GUILayout
from pyqtgraph.parametertree import Parameter, ParameterTree
from qtpy.QtWidgets import *
from qtpy.QtGui import *


class _EZPlugin(GUIPlugin):
    def __init__(self, name, toolbuttons=None, parameters=None, appendcatalog=None, centerwidget=None, bottomwidget=None):
        self.name = name

        self.centerwidget = centerwidget() if callable(centerwidget) else centerwidget
        self.bottomwidget = bottomwidget() if callable(bottomwidget) else bottomwidget
        self.rightwidget = ParameterTree()
        self.toolbar = QToolBar()

        if parameters:
            self.parameters = Parameter(name="Params", type="group", children=parameters)
            self.rightwidget.setParameters(self.parameters, showTop=False)

        if toolbuttons:
            for toolbutton in toolbuttons:
                self.addToolButton(*toolbutton)

        if appendcatalog:
            self.appendCatalog = appendcatalog

        self.stages = {
            "EZPlugin": GUILayout(self.centerwidget, right=self.rightwidget, bottom=self.bottomwidget, top=self.toolbar)
        }

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


def EZPlugin(name="TestPlugin", toolbuttons=None, parameters=None, appendcatalog=None, centerwidget=None, bottomwidget=None):
    """
    Quickly create a custom Xi-cam plugin.

    This function provides an easy-to-use interface for creating a customized
    Xi-cam plugin.

    Parameters
    ----------
    name : str
        The name of the plugin to create (the default is 'TestPlugin').
    toolbuttons : List[Tuple[str, Callable, (str)]]
        A list of tool buttons to create. A tool button will implement some
        action when the tool button is clicked. See the `Notes` section
        for more information.
    parameters : List[pyqtgraph.parametertree.Parameter]
        TODO
    appendheadertest
        TODO
    centerwidget : QWidget
        The widget displayed in the center of the plugin's GUI (the default is
        None, which creates an pyqtgraph.ImageView).
    bottomwidget : QWidget
        The widget displayed at the bottom (below the center) of the plugin's
        GUI (the default is None, which creates a pyqtgraph.PlotWidget).

    Returns
    -------
    EZPlugin derived type
        Returns an EZPlugin derived object of type `name`.

    Notes
    -----
    The `toolbutton` parameter is an iterable of tool buttons. Each
    tool button is an iterable with the following contents: the location of
    the icon for the button, an action (method) that is invoked when the button
    is triggered, and an optional text string for the button (e.g. when the
    mouse hovers over the button).

    """
    import pyqtgraph as pg

    if centerwidget is None:
        centerwidget = pg.ImageView
    if bottomwidget is None:
        bottomwidget = pg.PlotWidget
    return type(
        name,
        (_EZPlugin,),
        {
            "__init__": lambda self: _EZPlugin.__init__(
                self, name, toolbuttons, parameters, appendcatalog, centerwidget, bottomwidget
            )
        },
    )
