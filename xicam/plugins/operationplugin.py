"""TODO Module docstring"""
import inspect
import weakref
from typing import Collection, Tuple, Type, Union, List, Callable, Sequence
from collections import OrderedDict
from collections.abc import MutableMapping

from pyqtgraph.parametertree import Parameter

from xicam.core import msg

from .hints import PlotHint
from .plugin import PluginType


class OperationError(Exception):
    """Base exception for this module."""
    pass


class ValidationError(OperationError):
    """Exception raised for invalid OperationPlugin configurations.

    Attributes
    ----------
    operation : OperationPlugin
        Reference to the operation that failed its validation check.
    message : str
        Explanation of the error.
    """

    def __init__(self, operation, message):
        self.operation = operation
        self.message = message

    # def __repr__(self):
    #     return f"ValidationError({self.operation!r}, {self.message!r})"

    def __str__(self):
        """Returns a readable string for this exception."""
        return f"Validation failed for {self.operation}: {self.message}"


class _OperationDict(MutableMapping):
    """Internal mapping class that has reference to an associated operation.

    Implements the MutableMapping abstract class,
    providing custom behavior for __setitem__.
    Changing the value of the internal mapping will attempt to
    update the associated operation's Parameter value.

    Context: OperationPlugin.wireup_parameter will ensure that when a Parameter's
    value or fixed state is changed, the associated operation state
    (fixed[parameter.name()], filled_value[parameter.name())is changed as well.
    This class achieves synchronization in the opposite direction -
    when the operation state changes,
    the associated Parameter value / fixed state is updated.

    For example, if a value in Operation.filled_values changes ("strength" = 0.6),
    then we need to update the associated Parameter's value (if the Parameter exists).
    """
    def __init__(self, seq=None, op=None, opts_key: str = "value", **kwargs):
        self.mapping = {}
        if seq:
            self.mapping.update(seq)
        self.mapping.update(kwargs)
        self.operation = op
        self._opts_key = opts_key

    def __delitem__(self, key):
        del self.mapping[key]

    def __getitem__(self, item):
        return self.mapping[item]

    def __setitem__(self, key, value):
        self.mapping[key] = value
        if self.operation:
            if self.operation._parameter:
                group_parameter = self.operation._parameter()
                if group_parameter:
                    try:
                        group_parameter.child(key).setOpts(**{self._opts_key: value})
                        # group_parameter.child(key).setValue(value,
                        #                                     blockSignal=self._operation._set_value)
                    except Exception as e:
                        msg.logError(e)

    def __iter__(self):
        return iter(self.mapping)

    def __len__(self):
        return len(self.mapping)

    def __repr__(self):
        return f"{type(self).__name__}({self.mapping}, op={self.operation})"

    def copy(self):
        return _OperationDict(self.mapping.copy(), op=self.operation, opts_key=self._opts_key)


class OperationPlugin(PluginType):
    """A plugin that can be used to define an operation, which can be used in a Workflow.

    Note: use the `@operation` decorator to create an operation type.

    At its simplest level, an operation can be though of as a function.
    Any arguments (parameters) defined in the python function are treated as inputs for the operation.
    An operation's outputs are defined by the returned values of the python function.

    There are various methods available to help with modifying the operation's parameters.

    For more information on the attributes, see the documentation for their respective method
    (e.g. for more information on `limits`, see the `limits` method documentation).

    For an easy way to expose parameters in the GUI, use `OperationPlugin.as_parameter` in conjunction with
    `pyqtgraph.Parameter.create`.
    Note that only input parameters that have type hinting annotations will be included in the return value
    of `OperationPlugin.as_parameter`.

    Attributes
    ----------
    filled_values : dict
        Keys are the parameter names, values are the current values for the parameter.
    fixable : dict
        Keys are the parameter names, values are bools indicating whether or not the parameter
        is able to be fixed.
    fixed : dict
        Keys are the parameter names, values are bools indicating whether or not the parameter
        is fixed.
    input_names : Tuple[str, ...]
        Names (in order) of the input argument(s) for the operation. Note that if not provided,
        input names default to the argument names in the function signature.
    limits : dict
        Keys are the parameter names, values are the limits (which are a collection of floats).
    opts : dict
        Any additional options (kwargs) to be passed to the parameter (useful with pyqtgraph).
    output_names : Tuple[str, ...]
        Names (in order) of the output(s) for the operation.
    output_shape : dict
        Keys are the output parameter names, values are the expected shape of the output
        (which are of type list).
    units : dict
        Keys are the parameter names, values are units (of type str).
    visible : dict
        Keys are the pareameter names, values are bools indicating whehter or not the parameter
        is visible (when exposed using pyqtgraph).
    disabled : bool
        Whether or not the operation is disabled (default is False).
    display_name: str
        The name of the operation as it should be displayed to a user.
    hints : list
    input_descriptions : dict
        A mapping dict containing descriptions of each named input parameter
    output_descriptions : dict
        A mapping dict containing descriptions of each named output parameter

    Notes
    -----
    This class formally deprecates usage of the ProcessingPlugin API.

    Example
    --------
    Here, we define a function, then wrap it with the OperationPlugin decorator to make it an operation.

    >>> @OperationPlugin
    >>> def my_operation(x: int = 1, y: int = 2): -> int
    >>>     return x + y

    """
    needs_qt = False

    _func = None  # type: Callable
    filled_values = _OperationDict()  # type: _OperationDict
    fixable = {}  # type: dict
    fixed = _OperationDict(opts_key="fixed") # type: _OperationDict
    input_names = None  # type: Tuple[str]
    output_names = None  # type: Tuple[str]
    limits = {}  # type: dict
    opts = {}  # type: dict
    output_shape = {}  # type: dict
    units = {}  # type: dict
    visible = {}  # type: dict
    name = None  # type: str
    input_descriptions = {}  # type: dict
    output_descriptions = {}  # type: dict
    categories = None  # type: Sequence[Union[tuple, str]]
    hints = []

    def __init__(self, **filled_values):
        super(OperationPlugin, self).__init__()
        # Copy class dict information so that changes to instance don't propagate to class
        self.filled_values = self.filled_values.copy()
        self.filled_values.operation = self  # Need to add the operation ref to our OperationDict
        self.filled_values.update(filled_values)
        self.fixable = self.fixable.copy()
        self.fixed = self.fixed.copy()
        self.fixed.operation = self  # Need to add the operation ref to our OperationDict
        self.limits = self.limits.copy()
        self.opts = self.opts.copy()
        self.output_shape = self.output_shape.copy()
        self.units = self.units.copy()
        self.hints = self.hints.copy()
        self._parameter = None  # type: weakref.ref

    @classmethod
    def _validate(cls):
        """Validates the OperationPlugin's inputs and outputs."""

        # Capture any validation issues for use later when raising
        invalid_msg = ""
        # Define which "input" arg properties we want to check
        input_properties = {"fixable": cls.fixable,
                            "fixed": cls.fixed,
                            "limits": cls.limits,
                            "opts": cls.opts,
                            "units": cls.units,
                            "visible": cls.visible}
        # Check if all the attributes have a default value for each input param
        for arg in cls.input_names:
            for name, prop in input_properties.items():
                if prop and arg not in prop:
                    pass  # Do we want to enforce input default values?

        # Check if there is a 1:1 mapping from user-specified input_names to function args
        num_names = len(cls.input_names)
        num_args = len(inspect.signature(cls._func).parameters.keys())
        if num_names != num_args:
            invalid_msg += (f"Number of input_names given ({num_names}) "
                            f"must match number of inputs for the operation ({num_args}).")
        # Check if there are any input args that are not actually defined in the operation
        # e.g. 'x' is not a valid input in the case below:
        # @visible('x')
        # def func(a): return
        for name, prop in input_properties.items():
            for arg in prop.keys():
                if arg not in cls.input_names:
                    invalid_msg += f"\"{arg}\" is not a valid input for \"{name}\". "

        # Warn if there are no output_names defined
        if not len(cls.output_names):
            warning_msg = (f"No output_names have been specified for your operation {cls}; "
                           f"you will not be able to connect your operation's output(s) to "
                           f"any other operations.")
            msg.logMessage(warning_msg, level=msg.WARNING)

        # Define which "output" arg properties we want to check
        output_properties = {"output_shape": cls.output_shape}
        # Check if there are any output args that are not actually defined in the operation
        for name, prop in output_properties.items():
            for arg in prop.keys():
                if arg not in cls.output_names:
                    invalid_msg += f"\"{arg}\" is not a valid output for \"{name}\". "

        if invalid_msg:
            raise ValidationError(cls, invalid_msg)
        else:
            msg.logMessage(f"All args for {cls} are valid.")

    def __call__(self, **kwargs):
        """Allows this class to be used as a function decorator."""
        filled_kwargs = self.filled_values.copy()
        filled_kwargs.update(kwargs)
        return self._func(**filled_kwargs)

    def __str__(self):
        return f"OperationPlugin named {self.name}"

    @property
    def input_types(self) -> 'OrderedDict[str, Type]':
        """Returns the types of the inputs for the operation."""
        signature = inspect.signature(self._func)
        input_type_map = OrderedDict([(name, parameter.annotation) for name, parameter in signature.parameters.items()])
        return input_type_map

    @property
    def output_types(self) -> 'OrderedDict[str, Type]':
        """Returns the types of the outputs for the operation."""
        return_annotation = inspect.signature(self._func).return_annotation
        if not return_annotation or return_annotation is inspect.Signature.empty:
            return_annotation = tuple()

        output_type_map = OrderedDict(zip(self.output_names, return_annotation.__args__))
        return output_type_map

    def __reduce__(self):
        return OperationPlugin, tuple(), {'_func': self._func,
                                          'filled_values': self.filled_values,
                                          'input_names': self.input_names,
                                          'output_names': self.output_names}

    def as_parameter(self):
        """Return the operation's inputs as a ready-to-use object with pyqtgraph.

        A list of dictionaries is returned with each dictionary representing one of the operation's input parameters.
        Each dictionary represents the state of the input parameter;
        for example, its name, its default value, its type, etc.
        Note that only inputs that have been annotated with type-hinting
        and whose types are registered with pyqtgraph (PARAM_TYPES) will be included in this list.
        This list can be passed to `pyqtgraph.Parameter.create` to create a parameter tree widget.

        Alternative text:
        A list of dictionaries is returned where each dict is a best-effort attempt to represent each input parameter as a pyqtgraph Parameter.

        Returns
        -------
        parameters : list
            List of dictionaries; each dictionary represents the state of an input parameter
            (only applies to input parameters that are annotated with type-hinting).

        Notes
        -----
        For more information about pyqtgraph and Parameters,
        see http://www.pyqtgraph.org/documentation/parametertree/parameter.html?highlight=create#pyqtgraph.parametertree.Parameter.create
        """
        from pyqtgraph.parametertree.Parameter import PARAM_TYPES

        parameter_dicts = []
        for name, parameter in inspect.signature(self._func).parameters.items():
            if getattr(parameter.annotation, '__name__', None) in PARAM_TYPES:
                parameter_dict = dict()
                parameter_dict.update(self.opts.get(name, {}))
                parameter_dict['name'] = name
                parameter_dict[
                    'default'] = parameter.default if parameter.default is not inspect.Parameter.empty else None
                parameter_dict['value'] = self.filled_values[
                    name] if name in self.filled_values else parameter_dict['default']

                parameter_dict['type'] = getattr(self.input_types[name], '__name__', None)
                if name in self.limits:
                    parameter_dict['limits'] = self.limits[name]
                parameter_dict['units'] = self.units.get(name)
                parameter_dict['fixed'] = self.fixed.get(name)
                parameter_dict['fixable'] = self.fixable.get(name)
                parameter_dict['visible'] = self.visible.get(name, True)
                parameter_dict.update(self.opts.get(name, {}))

                parameter_dicts.append(parameter_dict)

            elif getattr(self.input_types[name], "__name__", None) == "Enum":
                parameter_dict = dict()
                parameter_dict['name'] = name
                parameter_dict['value'] = self.filled_values[
                    name] if name in self.filled_values else parameter.default
                parameter_dict['values'] = self.limits.get(name) or ["---"],
                parameter_dict['default'] = parameter.default
                parameter_dict['type'] = "list",
                if name in self.limits:
                    parameter_dict['limits'] = self.limits[name]
                parameter_dict['units'] = self.units.get(name)
                parameter_dict['fixed'] = self.fixed.get(name)  # TODO: Does this need a default value
                parameter_dict['fixable'] = self.fixable.get(name)
                parameter_dict['visible'] = self.visible.get(name, True)  # TODO: should we store the defaults at top?
                parameter_dict.update(self.opts.get(name, {}))

                parameter_dicts.append(parameter_dict)
        return parameter_dicts

    def wireup_parameter(self, parameter: Parameter):
        """Wire up a Parameter (created from an operation) to update the operation's state.

        Updates the operation's values (filled_values) if the Parameter values are changed.
        Updates the operatin's fixed state if the Parameter's fixed state is changed.

        This is useful when you want to interact with an operations inputs in a GUI
        by using something like a ParameterTree (see example).

        Parameters
        ----------
        parameter : Parameter
            A pyqtgraph Parameter created from an operation (via `as_parameter()`)

        Example
        -------
        >>> from pyqtgraph.parametertree import ParameterTree
        >>> from pyqtgraph.parametertree.parameterTypes import GroupParameter
        >>> from qtpy.QtWidgets import QApplication, QMainWindow
        >>> from xicam.plugins.operationplugin import operation, output_names
        >>> @operation
        >>> @output_names("sum")
        >>> def my_operation(x: float = 1.0, y: float = 2.0):
        >>>     return x + y
        >>> qapp = QApplication([])
        >>> parameter_tree = ParameterTree()
        >>> op = my_operation()
        >>> parameter = GroupParameter(name=op.name, children=op.as_parameter())
        >>> op.wireup_parameter(parameter)
        >>> parameter_tree.addParameters(parameter)
        >>> window = QMainWindow()
        >>> window.setCentralWidget(parameter_tree)
        >>> window.show()
        >>> qapp.exec_()
        """
        for child, param in zip(parameter.children(), self.as_parameter()):
            # wireup signals to update the workflow
            if param.get('fixable'):
                child.sigFixToggled.connect(self._set_fixed)
            msg.logMessage(child.name())
            # child.sigValueChanged.connect(lambda *args: print(args))
            child.sigValueChanged.connect(self._set_value)
            # We want to propagate changes to the operation's fixed/values state to the Parameter
            self._parameter = weakref.ref(parameter)

    def _set_fixed(self, param: Parameter, value):
        """Update the fixed state for the operation when it is toggled in the corresponding Parameter."""
        self.fixed[param.name()] = value

    def _set_value(self, param: Parameter, value):
        """Update the value for an operation when it is changed in he corresponding Parameter."""
        self.filled_values[param.name()] = value


def operation(func: Callable,
              filled_values: dict = None, fixable: dict = None, fixed: dict = None,
              input_names: Tuple[str, ...] = None, output_names: Tuple[str, ...] = None,
              limits: dict = None,
              opts: dict = None,
              output_shape: dict = None,
              units: dict = None,
              visible: dict = None,
              name: str = None,
              input_descriptions: dict = None, output_descriptions: dict = None,
              categories: Sequence[Union[tuple, str]] = None) -> Type[OperationPlugin]:
    """Create a new operation.

    *When you define a new operation, you must use this decorator (`@operation`)
    and the `@output_names` decorator.*

    This function can be used as a decorator to define a new operation type.
    The operation can then be instantiated by using the `()` operator on
    the operation function's name.

    Parameters
    ----------
    func : Callable
        Function that this operation will call.
    filled_values : dict, optional
        Values to fill for the parameters.
    fixable : dict, optional
        Indicates which parameters are able to be fixed.
    fixed :  dict, optional
        Indicates whether or not a parameter is fixed.
    limits : dict, optional
        Defines limits for parameters.
    opts : dict, optional
        Additional options (kwargs) for the parameter
        (useful with pyqtgraph's Parameter/ParameterTree).
    output_names : tuple, optional
        Names for the outputs, or returned values, of the operation.
    output_shape : dict, optional
        Defines expected shapes for the outputs.
    units : dict, optional
        Defines units for the parameters in the operation.
    name : str, optional
        The display name to be shown to the user. Defaults to self.__name__
    visible : dict, optional
        Indicates if a parameter is visible or not (see pyqtgraph.Parameter).
    input_descriptions : dict, optional
        A mapping dict containing descriptions for each named input
    output_descriptions : dict, optional
        A mapping dict containing descriptions for each named output
    categories : List[Union[tuple, str], optional
        A sequence of categories to associate with this operation.

    Example
    --------
    Create a new operation type and create a new operation instance from it.

    >>> from xicam.core.execution import Workflow
    >>> from xicam.plugins.operationplugin import operation, output_names
    >>> @operation
    >>> @output_names("my_output")
    >>> def my_func(x: float = 0.0) -> float:
    >>>     return x * -1
    >>> op = my_func()
    >>> workflow = Workflow()
    >>> result = workflow.execute(x=2.5).result()
    >>> print(result)

    """
    # For now, any C functions that don't have the required metadata for inspection will raise an exception
    # TODO: link to documentation
    try:
        inspect.signature(func)
    except ValueError as e:
        msg = f"The provided function '{func.__name__}' could not be inspected." \
               "In the case that your function is a C function, you will need to wrap it. " \
               "For an example, see the Xi-CAM.SAXS.processing.inpaint module."
        raise OperationError(msg) from e

    # Allow passing a string
    if type(input_names) is str:
        input_names = (input_names,)

    if type(output_names) is str:
        output_names = (output_names,)

    state = {  # "_func": func,
        "name": name or getattr(func, 'name', getattr(func, '__name__', None)),
        # Fallback to inspecting the function arg names if no input names provided
        "input_names": input_names or getattr(func,
                                              'input_names',
                                              tuple(inspect.signature(func).parameters.keys())),
        "output_names": output_names or getattr(func, 'output_names', getattr(func, "__name__", tuple())),
        "output_shape": output_shape or getattr(func, 'output_shape', {}),
        "input_description": input_descriptions or getattr(func, 'input_descriptions', {}),
        "output_descriptions": output_descriptions or getattr(func, 'output_descriptions', {}),
        "categories": categories or getattr(func, 'categories', []),
        "filled_values": _OperationDict(filled_values) or _OperationDict(),
        "limits": limits or getattr(func, 'limits', {}),
        "units": units or getattr(func, 'units', {}),
        "fixed": _OperationDict(fixed, opts_key="fixed") or
                 _OperationDict(getattr(func, 'fixed', {}), opts_key="fixed"),
        "fixable": fixable or getattr(func, 'fixable', {}),
        "visible": visible or getattr(func, 'visible', {}),
        "opts": opts or getattr(func, 'opts', {}),
        "hints": getattr(func, 'hints', [])  # TODO: does hints need an arg
    }

    if state["name"] is None:
        raise NameError('The provided operation is unnamed.')

    if type(state["output_names"]) == str:
        state["output_names"] = (state["output_names"],)

    operation_class = type("WrappedOperationPlugin", (OperationPlugin,), state)  # Ignore intellisense warnings
    operation_class._func = staticmethod(func)

    operation_class._validate()

    return operation_class


def _quick_set(func, attr_name, key, value, init):
    # TODO: does this need to be called initially to provide valid defaults?
    if not hasattr(func, attr_name):
        setattr(func, attr_name, init)
    getattr(func, attr_name)[key] = value


def display_name(name):
    """Set the display name for the operation.

    Display name is how this operation's name will be displayed in Xi-cam.

    Parameters
    ----------
    name : str
        Name for the operation.

    Example
    --------
    Create an operation whose display name is "Cube Operation."

    >>> @OperationPlugin
    >>> @display_name('Cube Operation')
    >>> def cube(n: int = 2) -> int:
    >>>     return n**3
    """

    def decorator(func):
        func.name = name
        return func

    return decorator


def units(arg_name, unit):
    """Decorator to define units for an input.

    Associates a unit of measurement with an input.

    Parameters
    ----------
    arg_name : str
        Name of the input to attach a unit to.
    unit : str
        Unit of measurement descriptor to use (e.g. "mm").

    Example
    --------
    Create an operation where its `x` parameter has its units defined in microns.

    >>> @OperationPlugin
    >>> @units('x', '\u03BC'+'m')
    >>> def op(x: float = -1) -> float:
    >>>     return x *= -1.0
    """

    def decorator(func):
        _quick_set(func, 'units', arg_name, unit, {})
        return func

    return decorator


def fixed(arg_name, fix=True):
    """Decorator to set whether or not an input's value is fixed.

    Fixed means that the input's value is fixed in the context of model fitting.

    By default, sets the `arg_name` input to fixed,
    meaning its value cannot be changed.

    Parameters
    ----------
    arg_name : str
        Name of the input to change fix-state for.
    fix : bool, optional
        Whether or not to fix `arg_name` (default is True).

    TODO example
    """

    def decorator(func):
        _quick_set(func, 'fixed', arg_name, fix, {})
        # TODO do we need to make 'fixed' args 'fixable'/'readonly'???
        # _quick_set(func, 'fixable', arg_name, True, {})
        return func

    return decorator


def limits(arg_name, limit):
    """Decorator to define limits for an input.

    Limits restrict the allowable values for the input
    (inclusive lower-bound, inclusive upper-bound).

    Parameters
    ----------
    arg_name : str
        Name of the input to define limits for.
    limit : tuple[float]
        A 2-element sequence representing the lower and upper limit.

    Example
    --------
    Make an operation that has a limit on the `x` parameter from [0, 100].

    >>> @OperationPlugin
    >>> @limits('x', [0, 100])
    >>> def op(x):
    >>>     ...

    Make an operation that has a limit on the `x` parameter from [0.0, 1.0].

    >>> @OperationPlugin
    >>> @limits('x', [0.0, 1.0])
    >>> @opts('x', step=0.1)
    >>> def op(x):
    >>>     ...

    """

    def decorator(func):
        _quick_set(func, 'limits', arg_name, limit, {})
        return func

    return decorator


# TODO: need an image_hint decorator? coplot_hint decorator?

# TODO Check that signature propagates up
def plot_hint(*args, **kwargs):
    """Decorator to define plot hints for 1-dimensional outputs. This accepts `kwargs` that get passed to the rendering
    widget; see :class:`pyqtgraph.PlotDataItem`. This annotation "hints" to Xi-cam that a Plot widget may be generated
    to represent this data visually.

    >>> @OperationPlugin
    >>> @output_names('x', 'y')
    >>> @plot_hint('x', 'y', yLog=True, labels={"left": "y-axis", "bottom": "x-axis"}, pen='r')
    >>> def op(x):
    >>>     ...

    Parameters
    ----------
    args
        Arguments for `PlotHint`.
    kwargs
        Keyword arguments for `PlotHint`.

    TODO examples may be helpful in these...
    """

    def decorator(func):
        if not hasattr(func, 'hints'):
            func.hints = []
        func.hints.append(PlotHint(*args, **kwargs))
        return func

    return decorator


def input_names(*names):
    """Decorator to define input names for the operation.

    The number of names provided must match the number of arguments for the operation/function.

    If not provided, input names will be determined by examining the names of the arguments
    to the operation function.

    Example
    --------
    Create an addition operation and use the names "first" and "second" for the input names
    instead of the function arg names (x and y).

    >>> @OperationPlugin
    >>> @input_names("first", "second")
    >>> def my_add(x: int, y: int) -> int:
    >>>     return x + y
    """

    def decorator(func):
        func.input_names = names
        return func

    return decorator


def output_names(*names):
    """Decorator to define the names of the outputs for an operation.

    Defines N-number of output names. These names will be used (in-order)
    to define any outputs that the operation has.

    Parameters
    ----------
    names : List[str]
        Names for the outputs in the operation.

    Example
    --------
    Define an operation that has the outputs `x` and `y`.

    >>> @OperationPlugin
    >>> @output_names("x", "y")
    >>> def some_operation(a: int, b: int) -> Tuple[int, int]:
    >>>     return a, b

    """

    def decorator(func):
        func.output_names = names
        return func

    return decorator


def output_shape(arg_name: str, shape: Union[int, Collection[int]]):
    # TODO: how does this work? How do we know the shape before runtime?
    """Decorator to set the shape of an output in an operation."

    Parameters
    ----------
    arg_name : str
        Name of the output to define a shape for.
    shape : int or tuple of ints
        N-element tuple representing the shape (dimensions) of the output.

    Example
    --------
    TODO
    """

    def decorator(func):
        _quick_set(func, 'output_shape', arg_name, shape, {})
        return func

    return decorator


def visible(arg_name: str, is_visible=True):
    """Decorator to set whether an input is visible (shown in GUI) or not.

    Parameters
    ----------
    arg_name : str
        Name of the input to change visibility for.
    is_visible : bool, optional
        Whether or not to make the input visible or not (default is True).

    Example
    --------
    Define an operation that makes the data_image invisible to the GUI (when using `as_parameter()` and pyqtgraph).

    >>> @OperationPlugin
    >>> @visible('data_image')
    >>> def threshold(data_image: np.ndarray, threshold: float = 0.5) -> np.ndarray:
    >>>     return ...

    """

    def decorator(func):
        _quick_set(func, 'visible', arg_name, is_visible, {})
        return func

    return decorator


def opts(arg_name: str, **options):
    """Decorator to set the opts (pyqtgraph Parameter opts) for `arg_name`.

    This is useful for attaching any extra attributes onto an operation input argument.

    These options correspond to the optional opts expected by pyqtgraph.Parameter.
    The options are typically used to add extra configuration to a Parameter.

    Parameters
    ----------
    arg_name : str
        Name of the input to add options for.
    options : keyword args
        Keyword arguments that can be used for the rendering backend (pyqtgraph).

    Example
    --------
    Define an operation where the `x` input is readonly.

    >>> @OperationPlugin
    >>> @opts('x', 'readonly'=True)
    >>> def op(x: str = 100) -> str:
    >>>     return x
    """

    def decorator(func):
        _quick_set(func, 'opts', arg_name, options, {})
        return func

    return decorator


def _describe_arg(arg_type: str, arg_name: str, description: str):
    assert arg_type in ['input', 'output']

    def decorator(func):
        _quick_set(func, f'{arg_type}_descriptions', arg_name, description, {})
        return func

    return decorator


def describe_input(arg_name: str, description: str):
    """Decorator to set the description for input `arg_name`.

    This is useful for annotating the parameter with additional information for users.

    These annotations are displayed in GUI representations of the operation.

    Parameters
    ----------
    arg_name : str
        Name of the input to add options for.
    description : str
        A human-readable description of the input `arg_name`

    Example
    --------
    Define an operation and attach a description to its `x` input argument.

    >>> @OperationPlugin
    >>> @describe_input('x', 'The value to square.')
    >>> def square(x: int = 100) -> int:
    >>>     return x**2
    """

    return _describe_arg('input', arg_name, description)


def describe_output(arg_name: str, description: str):
    """Decorator to set the description for output `arg_name`.

    This is useful for annotating the parameter with additional information for users.

    These annotations are displayed in GUI representations of the operation.

    Parameters
    ----------
    arg_name : str
        Name of the input to add options for.
    description : str
        A human-readable description of the output `arg_name`.

    Example
    --------
    Define an operation and attach a description to its `square` output.

    >>> @OperationPlugin
    >>> @output_names('square')
    >>> @describe_output('square', 'The squared value of x.')
    >>> def square(x: int = 100) -> int:
    >>>     return x**2
    """

    return _describe_arg('output', arg_name, description)


def categories(*categories: Tuple[Union[tuple, str]]):
    """Decorator to assign categories to a operation.

    These categories will be used to populate the structure of Xi-cam's menus of `OperationPlugins`.

    Parameters
    ----------
    categories : Tuple[Union[tuple, str]]
        A sequence of categories. Each item is a tuple or str. If an item is a tuple, each item in the tuple is considered
        as an additional depth in the menu structure.

    Example
    --------
    Define an operation that is in the following categories::

        Generic Functions
            Simple Math
                (square operation)
        Math Functions
                (square operation)

    >>> @OperationPlugin
    >>> @categories(('Generic Functions', 'Simple Math'), 'Math Functions')
    >>> def square(x: int = 100) -> int:
    >>>     return x**2
    """

    def decorator(func):
        if not hasattr(func, 'categories'):
            func.categories = []
        func.categories.append(categories)
        return func

    return decorator
