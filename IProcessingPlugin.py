from yapsy.IPlugin import IPlugin


class IProcessingPlugin(IPlugin):
    def __init__(self, *args, **kwargs):
        super(IProcessingPlugin, self).__init__()

    def evaluate(self):
        raise NotImplementedError


class Input(object):
    def __init__(self, name='', description='', default=None, unit=None, min=None, max=None, bounds=None):
        self.name = name
        self.description = description
        self.default = default
        self.unit = unit
        self.value = default