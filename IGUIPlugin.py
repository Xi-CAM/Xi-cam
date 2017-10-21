from yapsy.IPlugin import IPlugin
from typing import Dict,List
from collections import OrderedDict

class IGUIPlugin(IPlugin):
    def __init__(self):
        super(IGUIPlugin, self).__init__()
        self.stage = self.stages[0]

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
        raise NotImplementedError

    @property
    def exposedvars(self) -> Dict:
        raise NotImplementedError

class stage(object):
    def __init__(self,centerwidget,leftwidget,rightwidget,bottomwidget,topwidget):
        self.leftwidget = leftwidget
        self.rightwidget = rightwidget
        self.centerwidget = centerwidget
        self.bottomwidget = bottomwidget
        self.topwidget = topwidget