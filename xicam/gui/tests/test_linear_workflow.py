from pytestqt import qtbot
import pytest
from xicam.plugins.operationplugin import (display_name, fixed, input_names, limits, opts, output_names,
                                           output_shape, plot_hint, units, visible, ValidationError, operation)
from xicam.core.execution import Workflow
from xicam.gui.widgets.linearworkfloweditor import WorkflowEditor


@pytest.fixture
def square_op():
    @operation
    @output_names('square')
    def square(a=3) -> int:
        return a ** 2

    return square


@pytest.fixture
def sum_op():
    @operation
    @output_names('sum')
    def my_sum(a, b=3) -> int:
        return a + b

    return my_sum


@pytest.fixture
def qfit():
    from xicam.plugins import OperationPlugin, ProcessingPlugin, Input, Output, InOut, PlotHint
    import numpy as np
    from astropy.modeling import fitting
    from astropy.modeling import Fittable1DModel
    from typing import Tuple
    from enum import Enum
    from xicam.plugins import manager as pluginmanager
    from pyqtgraph.parametertree import Parameter

    class AstropyQSpectraFit(OperationPlugin):
        name = 'Q Fit (Astropy)'

        def __init__(self):
            super(AstropyQSpectraFit, self).__init__()

        def as_parameter(self):
            return [
                {"name": "Model", "type": "list", "limits": self.limits.get('model', {plugin.name: plugin for plugin in
                                                                                      pluginmanager.get_plugins_of_type(
                                                                                          'Fittable1DModelPlugin')})},
                {"name": "Model Parameters", "type": "group"}]

        def wireup_parameter(self, parameter):
            parameter.sigValueChanged.connect(self.value_changed)

        def value_changed(self, *args, **kwargs):
            print(args, kwargs)

        # TODO: model parameters could be set in the gui, but can they be connected programmatically?
        def _func(self, q, I, model: Fittable1DModel, domain_min=-np.inf, domain_max=np.inf,
                  fitter=fitting.LevMarLSQFitter, **model_parameters):
            for name, value in model_parameters.items():  # propogate user-defined values to the model
                getattr(model, name).value = value
                getattr(model, name).fixed = self.fixed.get(name)

            filter = np.logical_and(domain_min <= q, q <= domain_max)
            q = q[filter]
            I = I[filter]
            fitted_model = fitter()(model, q, I)
            fitted_profile = fitted_model(q)

            return fitted_model, fitted_profile

    return AstropyQSpectraFit


@pytest.fixture
def simple_workflow(square_op, sum_op):
    from xicam.core.execution.workflow import Workflow
    from xicam.core.execution.daskexecutor import DaskExecutor

    executor = DaskExecutor()

    wf = Workflow()

    square = square_op()
    square2 = square_op()
    square2.filled_values['a'] = 2
    my_sum = sum_op()

    wf.add_operation(square)
    wf.add_operation(square2)
    wf.add_operation(my_sum)
    wf.add_link(square, my_sum, 'square', 'a')
    wf.add_link(square2, my_sum, 'square', 'b')

    return wf


@pytest.fixture
def custom_parameter_workflow(qfit):
    from xicam.core.execution.workflow import Workflow
    from xicam.core.execution.daskexecutor import DaskExecutor
    from xicam.plugins import manager

    manager.collect_plugins()

    executor = DaskExecutor()

    wf = Workflow()

    qfit = qfit()

    wf.add_operation(qfit)
    return wf


def test_simple(simple_workflow: Workflow, qtbot):
    workflow_editor = WorkflowEditor(simple_workflow)
    workflow_editor.show()
    qtbot.addWidget(workflow_editor)


def test_custom_parameter(custom_parameter_workflow: Workflow, qtbot):
    workflow_editor = WorkflowEditor(custom_parameter_workflow)
    workflow_editor.show()
    qtbot.addWidget(workflow_editor)
    workflow_editor.workflowview.selectRow(
        0)  # Note: models is empty here because pluginmanger hasn't finished load yet
