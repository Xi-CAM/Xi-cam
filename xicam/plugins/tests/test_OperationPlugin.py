import pytest

import numpy as np

from xicam.core import msg

# from xicam.plugins import operation
from xicam.plugins.operationplugin import (
    display_name,
    fixed,
    input_names,
    limits,
    opts,
    output_names,
    output_shape,
    plot_hint,
    units,
    visible,
    ValidationError,
    operation,
)


# Tests both the function interface and Operation API interface
#
# the "test_defaults" cases test the absence of the tested decorator,
# i.e. what is the default initialized value for the tested decorator's
# associated attribute

# @fixed
class TestFixed:
    def test_defaults(self):
        def func(a, b):
            return

        # assert func.fixed == {}
        assert not hasattr(func, "fixed")
        # Test Operation API
        op = operation(func)
        assert op.fixed == {}

    def test_single(self):
        @fixed("a")
        def func(a, b):
            return

        assert func.fixed == {"a": True}
        # Test Operation API
        op = operation(func)
        assert op.fixed == {"a": True}

    def test_multiple(self):
        @fixed("a")
        @fixed("b")
        def func(a, b, c):
            return

        assert func.fixed == {"a": True, "b": True}
        # Test Operation API
        op = operation(func)
        assert op.fixed == {"a": True, "b": True}

    def test_explicit(self):
        @fixed("a", True)
        @fixed("b", False)
        def func(a, b, c):
            return

        assert func.fixed == {"a": True, "b": False}
        # Test Operation API
        op = operation(func)
        assert op.fixed == {"a": True, "b": False}

    def test_redundant(self):
        @fixed("b")
        @fixed("b")
        def func(a, b, c):
            return

        assert func.fixed == {"b": True}
        # Test Operation API
        op = operation(func)
        assert op.fixed == {"b": True}

    def test_no_parameter_with_name(self):
        @fixed("dne")
        def func(a, b, c):
            return

        assert func.fixed == {"dne": True}
        # Test Operation API
        with pytest.raises(ValidationError):
            operation(func)

    def test_bad(self):
        # TODO: do we need to test unexpected types?
        @fixed(3)
        def func(a):
            return

        assert True


# @limits
class TestLimits:
    def test_defaults(self):
        def func(a):
            return

        assert not hasattr(func, "limits")
        # Test Operation API
        op = operation(func)
        assert op.limits == {}

    def test_limits(self):
        @limits("a", [0.0, 1.0])
        def func(a):
            return

        assert func.limits == {"a": [0.0, 1.0]}
        # Test Operation API
        op = operation(func)
        assert op.limits == {"a": [0.0, 1.0]}


# @output_names
class TestOutputNames:
    def test_output_names(self):
        @output_names("sum")
        def my_sum(a, b):
            return np.sum(a, b)

        assert my_sum.output_names == ("sum",)
        # Test Operation API
        op = operation(my_sum)
        assert op.output_names == ("sum",)

    def test_output_names_none_provided(self, caplog):
        def my_op(a, b):
            return 42

        assert hasattr(my_op, "output_names") is False
        # Test Operation API
        op = operation(my_op)
        assert op.output_names == ("my_op", )
        # Expecting a msg.WARNING log record that mentions "output_names"
        expected_warn_record = caplog.records[0]
        assert expected_warn_record.levelno == msg.WARNING
        assert "output_names" in expected_warn_record.msg


# @input_names
class TestInputNames:
    def test_defaults(self):
        # Test not using the input_names decorator
        def my_op(x, y):
            return x + y

        assert hasattr(my_op, "input_names") is False
        # Test Operation API
        op = operation(my_op)
        assert op.input_names == ("x", "y")

    def test_matching_number_of_names(self):
        # Test a good use of the input_names decorator
        @input_names("first", "second")
        def my_sum(x, y):
            return x + y

        assert my_sum.input_names == ("first", "second")
        # Test the Operation API
        op = operation(my_sum)
        assert op.input_names == ("first", "second")

    def test_fewer_input_names(self):
        # Test when there are fewer input names given than there are function args
        @input_names("first")
        def my_sum(x, y):
            return x + y

        assert my_sum.input_names == ("first",)
        # Test the Operation API
        with pytest.raises(ValidationError):
            operation(my_sum)

    def test_extra_input_names(self):
        # Test when there are more input names given that there are function args
        @input_names("first", "second", "third", "fourth")
        def my_sum(x, y):
            return x + y

        assert my_sum.input_names == ("first", "second", "third", "fourth")
        # Test the Operation API
        with pytest.raises(ValidationError):
            operation(my_sum)


class TestOutputShape:
    def test_output_shape(self):
        # TODO: what should the expected shape be? A collection (list/tuple)?
        @output_shape("out", (10, 10))
        @output_names("out")
        def func(a) -> np.ndarray:
            return np.zeros(shape=(10, 10))

        assert func.output_shape == {"out": (10, 10)}
        # Test Operation API
        op = operation(func)
        assert op.output_shape == {"out": (10, 10)}

    def test_missing_output_name(self):
        # TODO: what should the expected shape be? A collection (list/tuple)?
        @output_shape("out", (10, 10))
        def func(a) -> np.ndarray:
            return np.zeros(shape=(10, 10))

        assert func.output_shape == {"out": (10, 10)}
        # Test Operation API
        with pytest.raises(ValidationError):
            operation(func)


# def test_plot_hint():
#     print('tlaktj')
#     assert False, 'bnlah'


# @units
class TestUnits:
    def test_defaults(self):
        def func(a):
            return

        assert not hasattr(func, "units")
        # Test Operation API
        op = operation(func)
        assert op.units == {}

    def test_units(self):
        @units("a", "mm")
        def func(a):
            return

        assert func.units == {"a": "mm"}
        # Test Operation API
        op = operation(func)
        assert op.units == {"a": "mm"}


# @display_name
class TestDisplayName:
    def test_defaults(self):
        def func(a):
            return

        assert not hasattr(func, "name")
        # Test Operation API
        op = operation(func)
        assert op.name == func.__name__

    def test_display_name(self):
        @display_name("my operation name")
        def func(a):
            return

        assert func.name == "my operation name"
        # Test Operation API
        op = operation(func)
        assert op.name == "my operation name"


# @visible
class TestVisible:
    def test_defaults(self):
        # TODO: what should this return?
        @output_names("z")
        def func(a):
            return

        # assert func.visible == {'a': True}  # Expects a default to be set regardless
        assert not hasattr(func, "visible")  # does not expect any defaults to be set; must be explicit
        # Test Operations API
        op = operation(func)
        assert op.visible == {}

    def test_default(self):
        @visible("a")
        def func(a, b):
            return

        assert func.visible == {"a": True}
        # Test Operations API
        op = operation(func)
        assert op.visible == {"a": True}

    def test_true(self):
        @visible("a", True)
        def func(a, b):
            return

        assert func.visible == {"a": True}
        # Test Operations API
        op = operation(func)
        assert op.visible == {"a": True}

    def test_false(self):
        @visible("a", False)
        def func(a, b):
            return

        assert func.visible == {"a": False}
        # Test Operations API
        op = operation(func)
        assert op.visible == {"a": False}


# @opts
class TestOpts:
    def test_defaults(self):
        def func(a):
            return

        assert not hasattr(func, "opts")
        # Test Operation API
        op = operation(func)
        assert op.opts == {}

    def test_opts(self):
        # TODO: what happens if you pass in an 'invalid' opt? what is an invalid opt?
        @opts("a", someopt="opt")
        def func(a, b):
            return

        assert func.opts == {"a": {"someopt": "opt"}}
        # Test Operation API
        op = operation(func)
        assert op.opts == {"a": {"someopt": "opt"}}


def test_as_parameter():
    @operation
    # @display_name('my_operation_name')
    @fixed("fixed_param")
    # @input_names('fixed', 'visible', 'limits', 'opts', 'units', 'unseen', 'default')
    @limits("limits_param", [0, 100])
    @opts("opts_param", opt="value")
    @output_names("out1", "out2")
    @output_shape("out1", [1])
    @units("units_param", "km")
    @visible("invisible_param", False)
    def func(
        fixed_param: int,
        invisible_param: int,
        limits_param: int,
        opts_param: list,
        units_param: float,
        unseen_param,
        default_param: int = 0,
    ):
        return

    expected_as_parameter = [
        {
            "default": None,
            "fixable": None,
            "fixed": True,
            "name": "fixed_param",
            "type": "int",
            "units": None,
            "value": None,
            "visible": True,
        },
        {
            "default": None,
            "fixable": None,
            "fixed": None,
            "name": "invisible_param",
            "type": "int",
            "units": None,
            "value": None,
            "visible": False,
        },
        {
            "default": None,
            "fixable": None,
            "fixed": None,
            "limits": [0, 100],
            "name": "limits_param",
            "type": "int",
            "units": None,
            "value": None,
            "visible": True,
        },
        {
            "default": None,
            "fixable": None,
            "fixed": None,
            "name": "opts_param",
            "opt": "value",
            "type": "list",
            "units": None,
            "value": None,
            "visible": True,
        },
        {
            "default": None,
            "fixable": None,
            "fixed": None,
            "name": "units_param",
            "type": "float",
            "units": "km",
            "value": None,
            "visible": True,
        },
        {
            "default": 0,
            "fixable": None,
            "fixed": None,
            "name": "default_param",
            "type": "int",
            "units": None,
            "value": 0,
            "visible": True,
        },
    ]

    assert func().as_parameter() == expected_as_parameter


# TODO: BrokenPipe and ValueError: I/O operation on closed file exceptions occur:
# * more than one of these workflow tests is run
# * one of the workflow tests is run, and a test above has a print() in it


def test_workflow():
    from xicam.core.execution.workflow import Workflow
    from xicam.core.execution.daskexecutor import DaskExecutor
    from xicam.plugins.operationplugin import output_names

    executor = DaskExecutor()

    @operation
    @output_names("square")
    def square(a=3) -> int:
        return a ** 2

    @operation
    @output_names("sum")
    def my_sum(a, b=3) -> int:
        return a + b

    wf = Workflow()

    square = square()
    my_sum = my_sum()

    wf.add_operation(square)
    wf.add_operation(my_sum)
    wf.add_link(square, my_sum, "square", "a")

    assert wf.execute_synchronous(executor=executor) == [{"sum": 12}]


@pytest.fixture
def square_op():
    @operation
    @output_names("square")
    def square(a=3) -> int:
        return a ** 2

    return square


@pytest.fixture
def sum_op():
    @operation
    @output_names("sum")
    def my_sum(a, b=3) -> int:
        return a + b

    return my_sum


def test_multiple_instances(square_op, sum_op):
    from xicam.core.execution.workflow import Workflow
    from xicam.core.execution.daskexecutor import DaskExecutor

    executor = DaskExecutor()

    wf = Workflow()

    square = square_op()
    square2 = square_op()
    square2.filled_values["a"] = 2
    my_sum = sum_op()

    wf.add_operation(square)
    wf.add_operation(square2)
    wf.add_operation(my_sum)
    wf.add_link(square, my_sum, "square", "a")
    wf.add_link(square2, my_sum, "square", "b")

    assert wf.execute_synchronous(executor=executor) == [{"sum": 13}]


#
#
# def test_autoconnect():
#     from xicam.core.execution.workflow import Workflow
#     from xicam.core.execution.daskexecutor import DaskExecutor
#     from xicam.plugins.operation import output_names
#
#     executor = DaskExecutor()
#
#     @operation
#     @output_names('square')
#     def square(a=3) -> int:
#         return a ** 2
#
#     @operation
#     @output_names('sum')
#     def my_sum(square, b=3) -> int:
#         return square + b
#
#     wf = Workflow()
#
#     wf.add_operation(square)
#     wf.add_operation(my_sum)
#     wf.auto_connect_all()
#
#     assert wf.execute_synchronous(executor=executor) == [{'sum': 12}]
