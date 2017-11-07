from yapsy.IPlugin import IPlugin


# TODO allow outputs/inputs to connect

class ProcessingPlugin(IPlugin):
    def __init__(self, *args, **kwargs):
        super(ProcessingPlugin, self).__init__()
        self._nameparameters()

    def evaluate(self):
        raise NotImplementedError

    def _nameparameters(self):
        self.parameters = []
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
    def __init__(self, name='', description='', default=None, type=None, unit=None, min=None, max=None, bounds=None):
        self.name = name
        self.description = description
        self.default = default
        self.unit = unit
        self.value = default
        self.min=min
        self.max=max
        self.type = None
        if bounds: self.min,self.max = bounds

    def __call__(self, value):
        self.value = value


class Output(object):
    def __init__(self, name='', description='', type=None, unit=None):
        self.name = name
        self.description = description
        self.unit = unit
        self.value = None
        self.type = type
