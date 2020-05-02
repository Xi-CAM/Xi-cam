from pytestqt import qtbot
import pytest
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
from xicam.core.execution import Workflow
from xicam.gui.widgets.linearworkfloweditor import WorkflowEditor
from xicam.core.tests.workflow_fixtures import square_op, sum_op, custom_parameter_op, custom_parameter_workflow, simple_workflow


def test_simple(simple_workflow: Workflow, qtbot):
    workflow_editor = WorkflowEditor(simple_workflow)
    workflow_editor.show()
    qtbot.addWidget(workflow_editor)


def test_custom_parameter(custom_parameter_workflow: Workflow, qtbot):
    workflow_editor = WorkflowEditor(custom_parameter_workflow)
    workflow_editor.show()
    qtbot.addWidget(workflow_editor)
    workflow_editor.workflowview.selectRow(0)  # Note: models is empty here because pluginmanger hasn't finished load yet
