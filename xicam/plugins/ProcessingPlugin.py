from yapsy.IPlugin import IPlugin
import inspect


# TODO allow outputs/inputs to connect

class ProcessingPlugin(IPlugin):
    isSingleton = False

    def __init__(self):
        super(ProcessingPlugin, self).__init__()
        self._clone_descriptors()
        self._nameparameters()
        self._param = None
        self.__internal_data__ = None

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

    def _clone_descriptors(self):
        for name, param in self.__class__.__dict__.items():
            if isinstance(param, (Input, Output)):
                param.name_from_instance(self)
                param.clone_to_instance(self)


                # for name, param in self.__dict__.items():
                #     if isinstance(param, (Input, Output)):
                #         param.name_from_instance(self)

    def _nameparameters(self):
        for name, param in self.__class__.__dict__.items():
            if isinstance(param, (Input, Output)):
                if not param.name:
                    param.name = name

    @property
    def inputs(self):
        return {name: param for name, param in self.__dict__.items() if isinstance(param, Input)}

    @property
    def inverted_inputs(self):
        return {param: name for name, param in self.__class__.__dict__.items() if isinstance(param, Input)}

    @property
    def outputs(self):
        return {name: param for name, param in self.__dict__.items() if isinstance(param, Output)}

    @property
    def inverted_outputs(self):
        return {param: name for name, param in self.__class__.__dict__.items() if isinstance(param, Output)}

    @property
    def parameter(self):

        from pyqtgraph.parametertree.Parameter import Parameter, PARAM_TYPES
        children = []
        for name, input in self.inputs.items():
            if getattr(input.type, '__name__') in PARAM_TYPES:
                childparam = Parameter.create(name=name,
                                              value=getattr(input, 'value', input.default),
                                              default=input.default,
                                              limits=[input.min, input.max],
                                              type=getattr(input.type, '__name__', None),
                                              units=input.units)
                childparam.sigValueChanged.connect(lambda param, value: self.setParameterValue(name, value))
                children.append(childparam)
        _param = Parameter(name=getattr(self, 'name', self.__class__.__name__), children=children, type='group')

        _param.sigValueChanged.connect(self.setParameterValue)
        return _param

    def setParameterValue(self, name, value):
        self.inputs[name].value = value


def EZProcessingPlugin(method):
    def __init__(self, method):
        self.method = method
        argspec = inspect.getfullargspec(method)
        self.inputs = [Input(name=argname) for argname in argspec.args + argspec.varargs + argspec.keywords]
        self.outputs = [Output(name='result')]
        super(EZProcessingPlugin, self).__init__()

    def evaluate(self):
        self.method(*[i.value for i in self.inputs])

    return type(method.__name__, (ProcessingPlugin,), {'__init__': __init__, 'evaluate': evaluate})


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
        self.value = default
        self.min = min
        self.max = max
        self.type = type
        if limits: self.min, self.max = limits

    def clone_to_instance(self, instance):
        clone = self.__class__(self.name, self.description, self.default, self.type, self.units, self.min, self.max)
        clone.parent = instance
        instance.inputs[self.name] = clone
        setattr(instance, self.name, clone)
        return clone

    def name_from_instance(self, instance):
        self.name = instance.inverted_inputs[self]

        # def __get__(self, instance, owner):
        #     self.name_from_instance(instance)
        #     return self.clone_to_instance(instance)

        # def __set__(self, instance, value):
        #     self.clone_to_instance(instance).value = value

    def __setattr__(self, name, value):
        import pickle
        if name == "value":
            try:
                pickle.dumps(value)
            except:
                print("cannot pickle", name, value)
            super().__setattr__(name, value)
        else:
            super().__setattr__(name, value)

class Output(Var):
    def __init__(self, name='', description='', type=None, units=None):
        super().__init__()
        self.name = name
        self.description = description
        self.units = units
        self.value = None
        self.type = type

    def clone_to_instance(self, instance):
        clone = self.__class__(self.name, self.description, self.type, self.units)
        clone.parent = instance
        instance.outputs[self.name] = clone
        setattr(instance, self.name, clone)
        return clone

    def name_from_instance(self, instance):
        self.name = instance.inverted_outputs[self]

        # def __get__(self, instance, owner):
        #     self.name_from_instance(instance)
        #     return self.clone_to_instance(instance)
        #
        # def __set__(self, instance, value):
        #     instance._output_values[self] = value
        #
        # def __delete__(self, instance):
        #     del instance._output_values[self]


class InOut(Input, Output):
    pass
