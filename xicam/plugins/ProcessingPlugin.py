from yapsy.IPlugin import IPlugin
import inspect
from xicam.core import msg
from distributed.protocol.serialize import serialize
from functools import partial

# TODO allow outputs/inputs to connect

class ProcessingPlugin(IPlugin):
    isSingleton = False

    def __new__(cls, *args, **kwargs):
        instance = super(ProcessingPlugin, cls).__new__(cls)
        instance.__init__(*args, **kwargs)
        for name, param in cls.__dict__.items():
            if isinstance(param, (InOut)):
                param.name = instance.inverted_vars[param]
                clone = param.__class__()
                clone.__dict__ = param.__dict__.copy()
                clone.parent = instance
                instance.inputs[param.name] = clone
                instance.outputs[param.name] = clone
                setattr(instance, param.name, clone)
            elif isinstance(param, (Output)):
                param.name = instance.inverted_vars[param]
                clone = param.__class__()
                clone.__dict__ = param.__dict__.copy()
                clone.parent = instance
                instance.outputs[param.name] = clone
                setattr(instance, param.name, clone)
            elif isinstance(param, (Input)):
                param.name = instance.inverted_vars[param]
                clone = param.__class__()
                clone.__dict__ = param.__dict__.copy()
                clone.parent = instance
                instance.inputs[param.name] = clone
                setattr(instance, param.name, clone)
        return instance

    def __init__(self, *args, **kwargs):
        super(ProcessingPlugin, self).__init__()
        self._param = None
        self.__internal_data__ = None
        self.disabled = False
        self._inputs = getattr(self, '_inputs', None)
        self._outputs = getattr(self, '_outputs', None)
        self._inverted_vars = None
        self.name = getattr(self, 'name', self.__class__.__name__)
        self._workflow = None

    def evaluate(self):
        raise NotImplementedError

    def _getresult(self):
        self.evaluate()
        return tuple(output.value for output in self.outputs.values())

    def asfunction(self, *args, **kwargs):
        for input, arg in zip(self.inputs.values(), args):
            input.value = arg
        for k, v in kwargs.items():
            if k in self.inputs:
                self.inputs[k].value = v
        return self._getresult()

    @property
    def inputs(self):
        if not self._inputs:
            self._inputs = {name: param for name, param in self.__dict__.items() if isinstance(param, Input)}
        return self._inputs

    @property
    def outputs(self):
        if not self._outputs:
            self._outputs = {name: param for name, param in self.__dict__.items() if isinstance(param, Output)}
        return self._outputs

    @property
    def inverted_vars(self):
        if not self._inverted_vars:
            self._inverted_vars = {param: name for name, param in self.__class__.__dict__.items() if
                                   isinstance(param, (Input, Output))}
        return self._inverted_vars

    @property
    def parameter(self):
        if not (hasattr(self, '_param') and self._param):
            from pyqtgraph.parametertree.Parameter import Parameter, PARAM_TYPES
            children = []
            for name, input in self.inputs.items():
                if getattr(input.type, '__name__', None) in PARAM_TYPES:
                    childparam = Parameter.create(name=name,
                                                  value=getattr(input, 'value', input.default),
                                                  default=input.default,
                                                  limits=[input.min, input.max],
                                                  type=getattr(input.type, '__name__', None),
                                                  units=input.units)
                    childparam.sigValueChanged.connect(partial(self.setParameterValue, name))
                    children.append(childparam)
                    input._param = childparam
            self._param = Parameter(name=getattr(self, 'name', self.__class__.__name__), children=children,
                                    type='group')

            self._param.sigValueChanged.connect(self.setParameterValue)
        return self._param

    def setParameterValue(self, name, param, value):
        if value is not None:
            self.inputs[name].value = value
        else:
            self.inputs[name].value = self.inputs[name].default

        self._workflow.update()

    def clearConnections(self):
        for input in self.inputs.values():
            input.map_inputs = []

    def __reduce__(self):
        d = self.__dict__.copy()
        if '_param' in d: del d['_param']
        return _ProcessingPluginRetriever(), (self.__class__.__name__, d)


class _ProcessingPluginRetriever(object):
    """
    When called with the containing class as the first argument,
    and the name of the nested class as the second argument,
    returns an instance of the nested class.
    """

    def __call__(self, pluginname, internaldata):
        from xicam.plugins import manager as pluginmanager

        # if pluginmanager hasn't collected plugins yet, then do it
        if not pluginmanager.loadcomplete: pluginmanager.collectPlugins()

        # look for the plugin matching the saved name and re-instance it
        for plugin in pluginmanager.getPluginsOfCategory('ProcessingPlugin'):
            if plugin.plugin_object.__name__ == pluginname:
                p = plugin.plugin_object()
                p.__dict__ = internaldata
                return p

        raise ValueError(f'No plugin found with name {pluginname}')


def EZProcessingPlugin(method):
    def __new__(cls, *args, **kwargs):
        instance = ProcessingPlugin.__new__(cls)
        return instance

    def __init__(self):
        ProcessingPlugin.__init__(self)

    def evaluate(self):
        self.method(*[i.value for i in self.inputs])

    argspec = inspect.getfullargspec(method)
    allargs = argspec.args
    if argspec.varargs: allargs += argspec.varargs
    if argspec.kwonlyargs: allargs += argspec.kwonlyargs

    _inputs = {argname: Input(name=argname) for argname in allargs}
    _outputs = {'result': Output(name='result')}

    attrs = {'__new__': __new__,
             '__init__': __init__,
             'evaluate': evaluate,
             'method': method,
             '_outputs': _inputs,
             '_inputs': _outputs,
             '_inverted_vars': None,
             }
    attrs.update(_inputs)
    attrs.update(_outputs)

    return type(method.__name__, (ProcessingPlugin,), attrs)


class Var(object):
    def __init__(self):
        self.workflow = None
        self.parent = None
        self.conn_type = None  # input or output
        self.map_inputs = []
        self.subscriptions = []

    def connect(self, var):
        # find which variable and connect to it.
        var.map_inputs.append([var.name, self])

    def disconnect(self, var):
        pass

    def subscribe(self, var):
        # find which variable and connect to it.
        self.subscriptions.append([var.name, var])
        self.map_inputs.append([self.name, var])

    def unsubscribe(self, var):
        pass


class Input(Var):
    def __init__(self, name='', description='', default=None, type=None, units=None, min=None, max=None, limits=None):
        super().__init__()
        self.name = name
        self.description = description
        self.default = default
        self.units = units
        self.min = min
        self.max = max
        self.type = type
        self.value = default
        if limits: self.min, self.max = limits

    def __setattr__(self, name, value):
        if name == "value":
            try:
                serialize(value)
            except:
                msg.logMessage(f"Value '{value}'on input '{name}' could not be cloudpickled.", level=msg.WARNING)
            super().__setattr__(name, value)
        else:
            super().__setattr__(name, value)

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, v):
        self._value = v
        if hasattr(self, '_param') and self._param:
            self._param.setValue(v)

    def __reduce__(self):
        d = self.__dict__.copy()
        if '_param' in d: del d['_param']
        return _ProcessingPluginRetriever(), (self.__class__.__name__, d)


class Output(Var):
    def __init__(self, name='', description='', type=None, units=None, *args, **kwargs):
        super().__init__()
        self.name = name
        self.description = description
        self.units = units
        self.value = None
        self.type = type


class InOut(Input, Output):
    pass
