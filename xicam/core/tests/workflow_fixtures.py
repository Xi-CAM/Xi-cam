import pytest

from xicam.core import execution
from xicam.core.execution import localexecutor
from xicam.core.execution.workflow import Graph, Workflow
from xicam.plugins import OperationPlugin
from xicam.plugins.operationplugin import output_names, operation, display_name
from pyqtgraph.parametertree import Parameter


@pytest.fixture()
def graph():
    return Graph()


@pytest.fixture()
def square_op():
    @operation
    def square(n: int) -> int:
        return n * n

    return square()


@pytest.fixture()
def sum_op():
    @operation
    def sum(n1: int, n2: int) -> int:
        return n1 + n2

    return sum()


@pytest.fixture()
def negative_op():
    @operation
    def negative(num: int) -> int:
        return -1 * num

    return negative()


@pytest.fixture()
def simple_workflow(square_op, sum_op):
    from xicam.core.execution.workflow import Workflow

    wf = Workflow()

    square = square_op
    square2 = square_op.__class__()
    square2.filled_values["n1"] = 2

    wf.add_operation(square)
    wf.add_operation(square2)
    wf.add_operation(sum_op)
    wf.add_link(square, sum_op, "square", "n1")
    wf.add_link(square2, sum_op, "square", "n2")

    return wf


@pytest.fixture()
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


@pytest.fixture()
def custom_parameter_workflow(custom_parameter_op):
    from xicam.core.execution.workflow import Workflow

    wf = Workflow()

    custom_parameter_op = custom_parameter_op()

    wf.add_operation(custom_parameter_op)
    return wf