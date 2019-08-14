from yapsy.IPlugin import IPlugin
import inspect
from xicam.core import msg
from distributed.protocol.serialize import serialize
from functools import partial
import numpy as np
from typing import Callable, Dict, Type
from collections import namedtuple
from typing import List
from warnings import warn


# TODO allow outputs/inputs to connect

class ProcessingPlugin(IPlugin):
    # TODO -- hints documentation
    # TODO: Categories documentation
    """
    A ProcessingPlugin defines a plugin that can process inputs and/or outputs
    in a workflow.

    A ProcessingPlugin can take in input variables and operate on the inputs via
    the `evaluate()` method. Typically, the `evaluate()` method would output 
    results to an `Output`. In-place processing can be accomplished with
    `InputOutput` variables.

    Attributes
    ----------
    disabled : bool
        Disables the processing plugin (the default is 'False'). This state 
        only applies when a workflow's variables are auto-connected; disabled
        operations are bypassed.
    name : str
        Name of the processing plugin (the default is the name of the class).

    Notes
    -----
    Must override the `evaluate()` method in derived classes.

    Examples
    --------
    Create a MaskProcessingPlugin that masks an array of input pixels.

    1. Define the input and output variables as class variables

    All processing variables (Input, Output, InputOutput) must be defined as class
    variables. In the example below, `data`, `min_threshold`, `mask`, and
    `masked_data` are the variables we define. When creating these variables, we
    should give them a description and a type.
    The description briefly describes the variable.
    The type represents what kind of data the variable will hold.

    The Input variables are `data` and `masked_data`. These are the inputs to
    be evaluated. The `data` variable is the pixel data that we will be applying
    some mask to. The `minimum_threshold` defines the minimum value that a pixel
    value must be; otherwise it will be masked.

    The InputOutput variable is `mask`. The mask is an input because we can
    define an initial mask to our process. During evaluation, any pixels that
    do not meet the minimum threshold will be added to this mask. We can then
    inspect the mask as an output to see the final mask applied to the input
    data.

    The Output variable is `masked_data`. This will store the pixel data after
    the mask is applied (i.e. this stores the pixels that were not part of the
    mask).

    2. Implement the evaluate() method.

    After defining our processing plugin's variables, we need to provide
    instructions for how to process these variables. We do this by implementing
    the evaluate() method as part of the MaskProcessingPlugin class.

    To access our variables inside of evaluate(), we can use the following syntax:
        `self.variable.value`,

    where variable is the name of our python variables we assigned our processing
    variables to earlier.
    When accessing the variable this way, it is important to keep in mind that
    the value returned to us will be the type that we defined earlier. For
    example, for our `data` variable, we gave it the type `np.ndarray`. This
    means when we access it through `self.data.value`, we get a numpy ndarray
    back.::

        class MaskProcessingPlugin(ProcessingPlugin):
            # Define variables here
            data = Input(description='Input data', type=np.ndarray)
            min_threshold = Input(description='Minimum value that will not be masked', type=float)
            mask = InputOutput(description='Mask array (1 indicates mask)', type=np.ndarray)
            masked_data = Output(description='Data after mask is applied', type=np.ndarray)

            def evaluate(self):
                # Operate on variables here
                # Access variables using self.variable.value
                data_shape = self.data.value.shape
                self.masked_data.value = np.zeros(data_shape)

                for i in range(self.data.value.shape[0]):
                    for j in range(self.data.value.shape[1]):
                        if self.data[i][j] < self.min_threshold:
                            self.mask.value[i][j] = 1  # 1 indicates mask
                        self.masked_data.value[i][j] = (not self.mask.value[i][j]) * self.data.value[i][j]



    """
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
        if not hasattr(self, 'hints'): self.hints = []
        for hint in self.hints: hint.parent = self

    def evaluate(self):
        """
        Implements the processing behavior.

        This method must be overriden to provide a processing implementation.
        """
        raise NotImplementedError

    def _getresult(self) -> Dict:
        """
        Evaluates the plugin and returns its outputs.

        """
        self.evaluate()
        outputs = {}
        for k, v in self.outputs.items():
            outputs[k] = v
        return outputs

    def asfunction(self, **kwargs) -> Dict:
        """
        Sets the values of any inputs via `kwargs`, evaluates, then returns
        the output variables.

        Parameters
        ----------
        kwargs
            Keywords corresponding to the name of an input variable, and the
            value to set the input variable's value to

        """
        for k, v in kwargs.items():
            if k in self.inputs:
                self.inputs[k].value = v
        return self._getresult()

    @property
    def inputs(self) -> Dict:
        if not self._inputs:
            self._inputs = {name: param for name, param in self.__dict__.items()
                            if isinstance(param, Input)}
        return self._inputs

    @property
    def outputs(self) -> Dict:
        if not self._outputs:
            self._outputs = {name: param for name, param in
                             self.__dict__.items() if isinstance(param, Output)}
        return self._outputs

    @property
    def inverted_vars(self) -> Dict:
        if not self._inverted_vars:
            self._inverted_vars = {param: name for name, param in
                                   self.__class__.__dict__.items() if
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
                                                  value=getattr(input, 'value',
                                                                input.default),
                                                  default=input.default,
                                                  limits=input.limits,
                                                  type=getattr(input.type,
                                                               '__name__',
                                                               None),
                                                  units=input.units,
                                                  fixed=input.fixed,
                                                  fixable=input.fixable,
                                                  visible=input.visible,
                                                  **input.opts)
                    childparam.sigValueChanged.connect(
                        partial(self.setParameterValue, name))
                    if input.fixable:
                        childparam.sigFixToggled.connect(input.setFixed)
                    children.append(childparam)
                    input._param = childparam
                elif getattr(input.type, '__name__', None) == 'Enum':
                    childparam = Parameter.create(name=name,
                                                  value=getattr(input, 'value',
                                                                input.default) or '---',
                                                  values=input.limits or [
                                                      '---'],
                                                  default=input.default,
                                                  type='list')
                    childparam.sigValueChanged.connect(
                        partial(self.setParameterValue, name))
                    children.append(childparam)
                    input._param = childparam

            self._param = Parameter(
                name=getattr(self, 'name', self.__class__.__name__),
                children=children,
                type='group')

            self._param.sigValueChanged.connect(self.setParameterValue)
        return self._param

    def setParameterValue(self, name, param, value):
        """
        Sets the `name` parameter's value to the passed value.

        """
        if value is not None:
            self.inputs[name].value = value
        else:
            self.inputs[name].value = self.inputs[name].default

        self._workflow.update()

    def clearConnections(self):
        for input in self.inputs.values():
            input._map_inputs = []

    def detach(self):
        pass

    def __reduce__(self):
        """
        Defines custom serialization of a ProcessingPlugin's attributes.

        This effectively allows a ProcessingPlugin to be un-serialized
        if the plugin is located in a different directory, provided that
        plugin info file (<plugin>.yapsy-plugin) is in a directory the
        PluginManager searches.

        Notes
        -----
        The `_param`, `_workflow`, and `parameter` attributes are not
        serialized.

        """
        d = self.__dict__.copy()
        blacklist = ['_param', '_workflow', 'parameter']
        for key in blacklist:
            if key in d:
                del d[key]
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
        if not pluginmanager.loadcomplete and not pluginmanager.loading: pluginmanager.collectPlugins()

        # look for the plugin matching the saved name and re-instance it
        for plugin in pluginmanager.getPluginsOfCategory('ProcessingPlugin'):
            if plugin.plugin_object.__name__ == pluginname:
                p = plugin.plugin_object()
                p.__dict__ = internaldata
                return p

        pluginlist = '\n\t'.join(
            [plugin.plugin_object.__name__ for plugin in
             pluginmanager.getPluginsOfCategory('ProcessingPlugin')])
        raise ValueError(
            f'No plugin found with name {pluginname} in list of plugins:{pluginlist}')


def EZProcessingPlugin(method: Callable) -> Type[ProcessingPlugin]:
    """
    Provides an easy-to-use but limited way to create a ProcessingPlugin
    for use in a workflow.

    Creates a new derived ProcessingPlugin type, where passed method's name
    is used as the new type's name.

    Examples
    --------

    """

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
    whitelist = set()
    """
    Defines a variable.

    Attributes
    ----------
    value : Num
        Value of the variable (the default is None).
    workflow : Workflow
        The workflow that this variable belongs to (the default is None).
    parent : ProcessingPlugin
        The processing plugin this variable belongs to (the default is None).

    """

    def __init__(self):
        self.value = None
        self.workflow = None
        self.parent = None
        self._map_inputs = []  # type: List[List[str, Var]]
        self._subscriptions = []

    def connect(self, var):
        # find which variable and connect to it.
        var._map_inputs.append([var.name, self])

    def disconnect(self, var):
        pass

    def subscribe(self, var):
        # find which variable and connect to it.
        self._subscriptions.append([var.name, var])
        self._map_inputs.append([self.name, var])

    def unsubscribe(self, var):
        pass

    def __reduce__(self):
        d = dict()
        for key in self.whitelist:
            d[key] = getattr(self, key)
        return self.__class__, tuple(d.values())


class Input(Var):
    whitelist = {'name', 'description', 'default', 'type', 'units', 'min',
                 'max', 'limits', 'fixed', 'fixable', 'visible', 'opts'}

    """
    Defines an input variable.

    Parameters
    ----------
    name : str, optional
        Name of the variable (the default is '').
    description : str, optional
        Describes the variable (the default is '').
    default : Num, optional
        Default value for the variable (the default is None).
    type : Type, optional
        Defines the type that the variable holds (the default is None)
    units : str, optional
        Defines the units of the variable (the default is None).
    min : Num, optional
        Minimum value the variable can store (the default is None).
    max : Num, optional
        Maximum value the variable can store (the default is None).
    limits : Tuple[Num, Num]
        Defines the minimum and maximum values the variable can store (the
        default is None).
    fixed : bool, optional
        Indicates if the variable is a fixed parameter (the default is False).
    fixable : bool, optional
        Indicates if the variable is able to be fixed or not as a parameter
        (the default is False).
    visible : bool, optional
        Indicates if the variable is visible on the parameter tree
        (the default is True).

    """
    def __init__(self, name='', description='', default=None, type=None,
                 units=None, min=None, max=None, limits=None,
                 fixed=False, fixable=False, visible=True, opts=None, **kwargs):

        self.fixed = fixed
        super(Input, self).__init__()
        self.name = name
        self.description = description
        self.default = default
        self.units = units
        self._limits = limits
        self.type = type
        self._value = default
        self.fixable = fixable
        self.visible = visible
        self.opts = opts or dict()
        self.opts.update(kwargs)
        if limits is None:
            self._limits = (min, max)

    @property
    def min(self):
        return self.limits[0]

    @property
    def max(self):
        return self.limits[1]

    @property
    def limits(self):
        if self._limits is None: return -np.inf, np.inf
        if len(self._limits) == 2:
            return self._limits[0] or -np.inf, self._limits[1] or np.inf
        return self._limits

    @limits.setter
    def limits(self, value):
        self._limits = value

    def __setattr__(self, name, value):
        if name == "value":
            try:
                serialize(value)
            except:
                # TODO: narrow except
                msg.logMessage(
                    f"Value '{value}'on input '{name}' could not be cloudpickled.",
                    level=msg.WARNING)
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
            self._param.blockSignals(True)
            self._param.setValue(v)
            self._param.blockSignals(False)

    def setFixed(self, fixed):
        self.fixed = fixed


class Output(Var):
    whitelist = {'name', 'description', 'type', 'units'}
    """
    Defines an output variable.

    Parameters
    ----------
    name : str, optional
        Name of the output variable (the default is '').
    description : str, optional
        Describes what the variable represents (the default is '').
    type : Type, optional
        Defines the type that the variable holds (the default is None).
    units : str
        Defines the units of the variable (the default is None).

    """

    def __init__(self, name='', description='', type=None, units=None):
        super(Output, self).__init__()
        self.name = name
        self.description = description
        self.units = units
        self.type = type


class InputOutput(Input, Output):
    whitelist = Input.whitelist | Output.whitelist
    """
    Represents a variable that acts both as in input and an output.
    """
    pass


class InOut(InputOutput):
    warn('InOut has been renamed; use InputOutput', DeprecationWarning)
