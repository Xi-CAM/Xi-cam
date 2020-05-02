import pytest

from xicam.core import execution
from xicam.core.execution import localexecutor
from xicam.core.execution.workflow import Graph, Workflow
from xicam.plugins import OperationPlugin
from xicam.plugins.operationplugin import output_names, operation
from pyqtgraph.parametertree import Parameter


@pytest.fixture(scope="session")
def graph():
    return Graph()


@pytest.fixture(scope="session")
def square_op():
    @operation
    def my_square(n: int) -> int:
        return n * n

    return my_square


@pytest.fixture(scope="session")
def sum_op():
    @operation
    def my_sum(n1: int, n2: int) -> int:
        return n1 + n2

    return my_sum


@pytest.fixture(scope="session")
def negative_op():
    @operation
    def my_negative(num: int) -> int:
        return -1 * num

    return my_negative


@pytest.fixture(scope="session")
def simple_workflow(square_op, sum_op):
    from xicam.core.execution.workflow import Workflow

    wf = Workflow()

    square = square_op()
    square2 = square_op()
    square2.filled_values["n1"] = 2
    my_sum = sum_op()

    wf.add_operation(square)
    wf.add_operation(square2)
    wf.add_operation(my_sum)
    wf.add_link(square, my_sum, "square", "n1")
    wf.add_link(square2, my_sum, "square", "n2")

    return wf


@pytest.fixture(scope="session")
def custom_parameter_op():
    class CustomParameterOp(OperationPlugin):
        def __init__(self):
            super(CustomParameterOp, self).__init__()
            self.value = False

        def _func(self):
            return self.value

        def as_parameter(self):
            return [{'name':'test', 'type':'bool'}]

        def wireup_parameter(self, parameter:Parameter):

            parameter.child('test').sigValueChanged.connect(lambda value: print(value))

    return CustomParameterOp


@pytest.fixture(scope="session")
def custom_parameter_workflow(custom_parameter_op):
    from xicam.core.execution.workflow import Workflow

    wf = Workflow()

    custom_parameter_op = custom_parameter_op()

    wf.add_operation(custom_parameter_op)
    return wf