from collections import OrderedDict
from enum import Enum
from typing import Dict, List, Union
from xicam.core.data import NonDBHeader
from qtpy.QtGui import *
from databroker.core import BlueskyRun

from .plugin import PluginType


class GUIPlugin(PluginType):
    """GUIPlugin class for interactive Xi-CAM plugins.

    This class represents the fundamental interactive plugin for Xi-CAM.

    GUIPlugins are left uninstanciated until all plugins are loaded so that all dependent widgets are loaded before
    the UI is setup. They DO become singletons.
    """

    is_singleton = True
    needs_qt = True

    def __init__(self):
        """Creates a GUIPlugin.

        When implementing your own GUIPlugin, you will want to set the `self.stages` property
        and then call `super` at the end of `__init__`.
        """
        super(GUIPlugin, self).__init__()
        self.stage = list(self.stages.values())[0]

    def appendHeader(self, header: NonDBHeader, **kwargs):
        # kwargs can include flags for how the data append operation is handled, i.e.:
        #   - as a new doc
        #   - merged into the current doc (stream)
        #   - as a new doc, flattened by some operation (average)
        pass

    def appendCatalog(self, catalog: BlueskyRun, **kwargs):
        """Re-implement to define how to add a catalog to your GUIPlugin.

        Parameters
        ----------
        catalog : BlueskyRun
            Catalog reference that you can use as you wish (corresponds to the opened catalog in DataResourceBrowser).
        """
        # kwargs can include flags for how the data append operation is handled, i.e.:
        #   - as a new doc
        #   - merged into the current doc (stream)
        #   - as a new doc, flattened by some operation (average)
        pass

    def currentheader(self) -> Dict:
        raise NotImplementedError

    @property
    def headers(self) -> List[NonDBHeader]:
        return [self.headermodel.item(i) for i in range(self.headermodel.rowCount())]

    @property
    def stages(self) -> OrderedDict:
        """Returns the stages of the GUIPlugin.

        A stage is defined by a GUILayout; each stage represents a distinct user-interface in a GUIPlugin.
        """
        return self._stages

    @stages.setter
    def stages(self, stages):
        """Set the GUIPlugin's stages"""
        self._stages = stages

    @property
    def exposedvars(self) -> Dict:
        raise NotImplementedError


class PanelState(Enum):
    """
    Represents the state of a panel (widget). Some panels have default
    widgets. The data preview widget and data browser widget are defaults
    for the top-left and left panels respectively. In order to not show
    these widgets, PanelState.Disabled must be set to those panels.

    """

    Disabled = 1
    Defaulted = 2
    Customized = 3


class GUILayout(object):
    """
    Represents a layout of dockable widgets in a 3x3 grid.

    The parameters can either be a PanelState value or a QWidget object. Note
    that only the `center` parameter is required; the other parameters default
    to `PanelState.Defaulted`. The default behavior of a `PanelState.Defaulted`
    widget is to be hidden.

    Parameters
    ----------
    center : Union[QWidget, PanelState]
        The center widget
    left : Union[QWidget, PanelState], optional
        The left widget
    right : Union[QWidget, PanelState], optional
        The right widget
    bottom : Union[QWidget, PanelState], optional
        The bottom widget
    top : Union[QWidget, PanelState], optional
        The top widget
    lefttop : Union[QWidget, PanelState], optional
        The top-left widget
    righttop : Union[QWidget, PanelState], optional
        The top-right widget
    leftbottom : Union[QWidget, PanelState], optional
        The bottom-left widget
    rightbottom : Union[QWidget, PanelState], optional
        The bottom-right widget

    Notes
    -----
    For an example of how this class can be used, see the xicam.gui
    XicamMainWindow class.

    """

    def __init__(
        self,
        center,
        left=PanelState.Defaulted,
        right=PanelState.Defaulted,
        bottom=PanelState.Defaulted,
        top=PanelState.Defaulted,
        lefttop=PanelState.Defaulted,
        righttop=PanelState.Defaulted,
        leftbottom=PanelState.Defaulted,
        rightbottom=PanelState.Defaulted,
    ):
        self.topwidget = top
        self.leftwidget = left
        self.rightwidget = right
        self.centerwidget = center
        self.bottomwidget = bottom
        self.lefttopwidget = lefttop
        self.righttopwidget = righttop
        self.leftbottomwidget = leftbottom
        self.rightbottomwidget = rightbottom

    def __getitem__(self, item: str):
        if not item.endswith("widget"):
            item += "widget"
        return getattr(self, item, PanelState.Defaulted)
