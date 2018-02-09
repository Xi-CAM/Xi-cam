from yapsy.IPlugin import IPlugin


# TODO allow outputs/inputs to connect

class ProcessingPlugin(IPlugin):
    def __init__(self, *args, **kwargs):
        super(ProcessingPlugin, self).__init__()
        self._clone_descriptors()
        self._nameparameters()
        self.__internal_data__ = None

    def evaluate(self):
        raise NotImplementedError

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
                    param.name=name

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

class Var(object):
    def __init__(self):
        self.workflow = None
        self.parent = None
        self.conn_type = None # input or output
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
    def __init__(self, name='', description='', default=None, type=None, unit=None, min=None, max=None, bounds=None):
        super().__init__()
        self.name = name
        self.description = description
        self.default = default
        self.unit = unit
        self.value = default
        self.min=min
        self.max=max
        self.type = None
        if bounds: self.min,self.max = bounds

    def clone_to_instance(self, instance):
        clone = self.__class__(self.name, self.description, self.default, self.unit, self.value,
                               self.min, self.max)
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
        if name=="value":
            try:
              pickle.dumps(value)
            except:
              print("cannot pickle", name, value)
            super().__setattr__(name, value)
        else:
            super().__setattr__(name, value)

class Output(Var):
    def __init__(self, name='', description='', type=None, unit=None):
        super().__init__()
        self.name = name
        self.description = description
        self.unit = unit
        self.value = None
        self.type = type

    def clone_to_instance(self, instance):
        clone = self.__class__(self.name, self.description, self.type, self.unit)
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
