from yapsy.IPlugin import IPlugin


class IProcessingPlugin(IPlugin):
    def __init__(self, *args, **kwargs):
        super(IProcessingPlugin, self).__init__()
        self._nameparameters()

    def evaluate(self):
        raise NotImplementedError

    def _nameparameters(self):
        self.parameters=[]
        for name, param in self.__class__.__dict__.items():
            if isinstance(param, (Input, Output)):
                if not param.name:
                    param.name=name

    @property
    def inputs(self):
        return {name:param for name, param in self.__class__.__dict__.items() if isinstance(param, Input)}

    @property
    def outputs(self):
        return {name:param for name, param in self.__class__.__dict__.items() if isinstance(param, Output)}

class Input(object):
    def __init__(self, name='', description='', default=None, unit=None, min=None, max=None, bounds=None):
        self.name = name
        self.description = description
        self.default = default
        self.unit = unit
        self.value = default
        self.min=min
        self.max=max
        if bounds: self.min,self.max = bounds


class Output(object):
    def __init__(self, name='', description='', unit=None):
        self.name = name
        self.description = description
        self.unit = unit
        self.value = None
