import inspect
from typing import List, Union
from pyqtgraph.parametertree import Parameter, parameterTypes, ParameterTree
from pyqtgraph.parametertree.Parameter import PARAM_TYPES
from qtpy.QtWidgets import QDialog, QVBoxLayout, QDialogButtonBox
from qtpy.QtCore import Qt

"""
Usage:

parameterized_scan = ParameterizablePlan(scan)

plan = parameterized_scan([det], device_list(), min, max)

plan_parameter = plan.parameter

RE(plan)

"""


class ParameterizablePlan(object):
    def __init__(self, plan):
        self.plan = plan

    def __call__(self, *args, **kwargs):
        return ParameterizedPlan(self.plan, args, kwargs)


class ParameterizedPlan(object):
    def __init__(self, plan, args, kwargs):
        self.plan = plan
        self.args = args
        self.kwargs = kwargs
        self._parameter = None

    @property
    def parameter(self):
        if not self._parameter:
            self._parameter = args_to_params(*self.args, **self.kwargs)
        return self._parameter

    def __iter__(self):
        args = list(self.args)
        kwargs = dict()
        for i, arg in enumerate(args):
            if isinstance(arg, Parameter):
                args[i] = arg.value()
            else:
                args[i] = arg

        for key, value in self.kwargs.items():
            if isinstance(value, Parameter):
                kwargs[key] = value.value()
            else:
                kwargs[key] = value

        return self.plan(*args, **kwargs)

    # def __next__(self):
    #     if not self._plan_instance:
    #         self._plan_instance = self.plan(*self.args, **self.kwargs)
    #     return next(self._plan_instance)


def parameterize(func):
    """
    Usage:

    from pyqtgraph.parametertree.parameterTypes import SimpleParameter

    @parameterize
    def sum(a, b):
        return sum(a, b)

    a = SimpleParameter(name='a', type='float', value=1)
    b = SimpleParameter(name='b', type='float', value=2)

    sum(a, b)  # spawns a dialog; user-interaction required
    """

    def func_wrapper(*args, **kwargs):
        param = args_to_params(*args, **kwargs)

        # query values
        paramdialog = ParameterDialog(param)
        paramdialog.exec_()

        # extract values
        args = list(args)
        for i, arg in enumerate(args):
            if isinstance(arg, Parameter):
                args[i] = arg.value()
            else:
                args[i] = arg

        for key, value in kwargs.items():
            if isinstance(value, Parameter):
                kwargs[key] = value.value()
            else:
                kwargs[key] = value

        # make the call
        return func(*args, **kwargs)

    return func_wrapper


def args_to_params(*args, **kwargs):
    param = parameterTypes.GroupParameter(name="Parameters")
    for arg in args + tuple(kwargs.values()):
        if isinstance(arg, Parameter):
            param.addChild(arg)
        elif isinstance(arg, (list, tuple)) and len(arg):
            child = args_to_params(*arg)
            if len(child.childs):
                param.addChild(child)
    return param


class ParameterDialog(QDialog):
    def __init__(self, children, parent=None):
        super(ParameterDialog, self).__init__(parent)

        layout = QVBoxLayout(self)

        self.paramtree = ParameterTree()
        layout.addWidget(self.paramtree)

        self.paramtree.setParameters(children, showTop=False)

        # OK and Cancel buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, Qt.Horizontal, self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def exec_(self, *args, **kwargs):
        result = super(ParameterDialog, self).exec_()
        if result != self.Accepted:
            raise InterruptedError("Execution aborted by user.")


def signature_to_param(signature: inspect.Signature,
                       opts: dict = None,
                       filled_values: dict = None,
                       display_names: dict = None,
                       limits: dict = None,
                       units: dict = None,
                       fixed: dict = None,
                       visible: dict = None,
                       fixable: dict = None):

    if not opts: opts = {}
    if not filled_values: filled_values = {}
    if not display_names: display_names = {}
    if not limits: limits = {}
    if not units: units = {}
    if not fixed: fixed = {}
    if not fixable: fixable = {}
    if not visible: visible = {}

    parameter_dicts = []

    for display_name, (name, parameter) in zip(display_names, signature.parameters.items()):
        param_type = param_type_from_annotation(parameter.annotation)

        if not param_type: continue

        parameter_dict = dict()
        parameter_dict.update(opts.get(name, {}))
        parameter_dict['name'] = display_name or name
        parameter_dict[
            'default'] = parameter.default if parameter.default is not inspect.Parameter.empty else None
        parameter_dict['value'] = filled_values[
            name] if name in filled_values else parameter_dict['default']
        parameter_dict['type'] = param_type
        if name in limits:
            parameter_dict['limits'] = limits[name]
        elif param_type == 'EnumMeta':
            parameter_dict['limits'] = {enum.name: enum.value for enum in parameter.annotation.__members__.values()}
        parameter_dict['units'] = units.get(name)
        parameter_dict['fixed'] = fixed.get(name)
        parameter_dict['fixable'] = fixable.get(name)
        parameter_dict['visible'] = visible.get(name, True)
        parameter_dict.update(opts.get(name, {}))

        parameter_dicts.append(parameter_dict)

    return parameter_dicts


def param_type_from_annotation(annotation) -> str:
    if getattr(annotation, '__name__', None) in PARAM_TYPES:
        return getattr(annotation, '__name__', None)
    elif getattr(getattr(annotation, '__class__', object), '__name__', None) in PARAM_TYPES:
        return getattr(getattr(annotation, '__class__', object), '__name__', None)
    elif getattr(annotation, '__origin__', None) is Union:  # For Union, try types in sequence
        for unioned_type in annotation.__args__:
            type_name = getattr(unioned_type, '__name__')
            if type_name in PARAM_TYPES:
                return type_name
    else:
        return None