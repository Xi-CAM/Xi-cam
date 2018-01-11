from yapsy.IPlugin import IPlugin


# TODO allow outputs/inputs to connect

class ProcessingPlugin(IPlugin):
    def __init__(self, *args, **kwargs):
        super(ProcessingPlugin, self).__init__()
        self._clone_descriptors()
        self._nameparameters()

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

    def clone_to_instance(self, instance):
        clone = self.__class__(self.name, self.description, self.default, self.unit, self.value,
                               self.min, self.max)
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


class Output(object):
    def __init__(self, name='', description='', type=None, unit=None):
        self.name = name
        self.description = description
        self.unit = unit
        self.value = None
        self.type = type

    def clone_to_instance(self, instance):
        clone = self.__class__(self.name, self.description, self.type, self.unit)
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
