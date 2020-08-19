from pytestqt import qtbot
from xicam.core.execution import Workflow
from xicam.gui.widgets.linearworkfloweditor import WorkflowEditor
from xicam.core.tests.workflow_fixtures import square_op, sum_op, custom_parameter_op, custom_parameter_workflow, simple_workflow


def test_simple(simple_workflow: Workflow, square_op, qtbot):
    workflow_editor = WorkflowEditor(simple_workflow)
    simple_workflow.add_operation(square_op.clone())
    workflow_editor.show()
    qtbot.addWidget(workflow_editor)


def test_custom_parameter(custom_parameter_workflow: Workflow, qtbot):
    workflow_editor = WorkflowEditor(custom_parameter_workflow)
    workflow_editor.show()
    qtbot.addWidget(workflow_editor)
    workflow_editor.workflowview.setCurrentIndex(workflow_editor.workflowview.model().createIndex(0,0))  # Note: models is empty here because pluginmanger hasn't finished load yet
