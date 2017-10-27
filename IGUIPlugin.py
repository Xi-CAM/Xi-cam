from collections import OrderedDict
from enum import Enum
from typing import Dict, List

from yapsy.IPlugin import IPlugin


class IGUIPlugin(IPlugin):
    def __init__(self):
        super(IGUIPlugin, self).__init__()
        self._stages = OrderedDict()
        self.stage = list(self.stages.values())[0]

    def appendDocuments(self, doc:List[dict], **kwargs):
        # kwargs can include flags for how the data append operation is handled, i.e.:
        #   - as a new doc
        #   - merged into the current doc (stream)
        #   - as a new doc, flattened by some operation (average)
        raise NotImplementedError

    def currentDocument(self) -> Dict:
        raise NotImplementedError

    @property
    def documents(self) -> OrderedDict:
        raise NotImplementedError

    @property
    def stages(self) -> OrderedDict:
        return self._stages

    @stages.setter
    def stages(self, stages):
        self._stages = stages

    @property
    def exposedvars(self) -> Dict:
        raise NotImplementedError


class PanelState(Enum):
    Disabled = 1
    Defaulted = 2
    Customized = 3


class GUILayout(object):
    def __init__(self, center, left=PanelState.Defaulted, right=PanelState.Defaulted, bottom=PanelState.Defaulted,
                 lefttop=PanelState.Defaulted, righttop=PanelState.Defaulted, leftbottom=PanelState.Defaulted,
                 rightbottom=PanelState.Defaulted):
        self.centerwidget = center
        self.leftwidget = left
        self.rightwidget = right
        self.bottomwidget = bottom
        self.lefttopwidget = lefttop
        self.righttopwidget = righttop
        self.leftbottomwidget = leftbottom
        self.rightbottomwidget = rightbottom
