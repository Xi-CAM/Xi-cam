from pytestqt import qtbot
from qtpy.QtCore import Qt
from xicam.core.execution import Workflow
from xicam.core.tests.workflow_fixtures import *
from xicam.plugins import manager
from xicam.gui.widgets.linearworkfloweditor import WorkflowEditor


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


def test_menu(simple_workflow, qtbot):
    manager.qt_is_safe = True
    manager.initialize_types()
    manager.collect_plugins()

    workflow_editor = WorkflowEditor(simple_workflow)
    workflow_editor.show()
    qtbot.addWidget(workflow_editor)
    # qtbot.wait(1000)
    # qtbot.mouseClick(workflow_editor.workflow_widget.addfunctionmenu, Qt.LeftButton)
    # qtbot.mouseClick(workflow_editor, Qt.LeftButton)
    # print(f"DEBUG: {workflow_editor.workflow_widget.functionmenu.pos()}")
    # # qtbot.mouseClick(workflow_editor.workflow_widget.functionmenu.)
    # # assert workflow_editor.workflow_widget.addfunctionmenu.isDown() == True
    # qtbot.wait(1000)


def test_workflow_selector(simple_workflow: Workflow, custom_parameter_workflow: Workflow, square_op, qtbot):
    workflow_editor = WorkflowEditor(simple_workflow,
                                     workflows={simple_workflow: 'Simple', custom_parameter_workflow: "Custom"})
    simple_workflow.add_operation(square_op.clone())
    workflow_editor.show()
    qtbot.addWidget(workflow_editor)
