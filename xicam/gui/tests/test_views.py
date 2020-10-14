import pytest
import numpy as np
from qtpy.QtCore import QModelIndex, Qt
from scipy import misc, ndimage
from qtpy.QtWidgets import QWidget, QHBoxLayout
from databroker.in_memory import BlueskyInMemoryCatalog
from pytestqt import qtbot
from xicam.plugins import manager as plugin_manager

from xicam.core.execution.workflow import Workflow, ingest_result_set, project_intents
from xicam.core import execution
from xicam.core.execution.localexecutor import LocalExecutor
from xicam.core.intents import PlotIntent, ImageIntent
from xicam.core.workspace import Ensemble
from xicam.gui.widgets.views import DataSelectorView, StackedCanvasView
from xicam.plugins.operationplugin import operation, output_names, intent
from xicam.gui.widgets.linearworkfloweditor import WorkflowEditor
from xicam.gui.models import EnsembleModel, IntentsModel


# TODO: move these fixtures into workflow_fixtures (when others use it)
@pytest.fixture()
def plot_op():
    @operation
    @output_names("output1", "output2")
    @intent(PlotIntent, name="X vs Y", output_map={"x": "output1", "y": "output2"}, labels={"bottom": "x", "left": "y"})
    def plot():
        x = np.asarray(list(range(1, 11)))
        y = np.random.randint(-10, 10+1, size=10)
        return x, y
    return plot()


@pytest.fixture()
def abs_plot_op():
    @operation
    @output_names("output1", "output2")
    @intent(PlotIntent, name="X vs Y", output_map={"x": "output1", "y": "output2"}, labels={"bottom": "x", "left": "y"})
    def abs_plot(x_arr: np.ndarray, y_arr: np.ndarray):
        return x_arr, np.abs(y_arr)
    return abs_plot()


@pytest.fixture()
def image_op():
    @operation
    @output_names("output_array")
    @intent(ImageIntent, name="Raccoon Image", output_map={"image": "output_array"})
    def image():
        return misc.face()
    return image()


@pytest.fixture()
def blur_image_op():
    @operation
    @output_names("output_array")
    @intent(ImageIntent, name="Blurred Raccoon Image", output_map={"image": "output_array"})
    def blur_image(arr: np.ndarray, blur=5):
        return ndimage.gaussian_filter(arr, sigma=blur)
    return blur_image()


@pytest.fixture()
def simple_workflow_with_intents(plot_op, abs_plot_op, blur_image_op, image_op):
    wf = Workflow()

    wf.add_operation(image_op)
    wf.add_operation(blur_image_op)
    wf.add_link(image_op, blur_image_op, "output_array", "arr")

    wf.add_operation(plot_op)
    wf.add_operation(abs_plot_op)
    wf.add_link(plot_op, abs_plot_op, "output1", "x_arr")
    wf.add_link(plot_op, abs_plot_op, "output2", "y_arr")

    return wf


def test_view(simple_workflow_with_intents, qtbot):
    # Tests ingesting an internally run workflow, projecting it, storing it in a model
    # and using a CanvasView to display it

    plugin_manager.qt_is_safe = True
    plugin_manager.initialize_types()
    plugin_manager.collect_plugins()

    pc = next(filter(lambda task: task.name == 'plot_canvas', plugin_manager._tasks))
    plugin_manager._load_plugin(pc)
    plugin_manager._instantiate_plugin(pc)

    ic = next(filter(lambda task: task.name == 'image_canvas', plugin_manager._tasks))
    plugin_manager._load_plugin(ic)
    plugin_manager._instantiate_plugin(ic)

    plot_intent_task = next(filter(lambda task: task.name == 'PlotIntent', plugin_manager._tasks))
    plugin_manager._load_plugin(plot_intent_task)
    plugin_manager._instantiate_plugin(plot_intent_task)
    image_intent_task = next(filter(lambda task: task.name == 'ImageIntent', plugin_manager._tasks))
    plugin_manager._load_plugin(image_intent_task)
    plugin_manager._instantiate_plugin(image_intent_task)

    execution.executor = LocalExecutor()
    ensemble_model = EnsembleModel()
    intents_model = IntentsModel()
    intents_model.setSourceModel(ensemble_model)

    data_selector_view = DataSelectorView()
    data_selector_view.setModel(ensemble_model)

    stacked_canvas_view = StackedCanvasView()
    stacked_canvas_view.setModel(intents_model)

    widget = QWidget()
    layout = QHBoxLayout()
    layout.addWidget(stacked_canvas_view)
    layout.addWidget(data_selector_view)
    widget.setLayout(layout)

    def showResult(*result):
        ensemble = Ensemble()
        doc_generator = ingest_result_set(simple_workflow_with_intents, result)

        documents = list(doc_generator)
        catalog = BlueskyInMemoryCatalog()
        catalog.upsert(documents[0][1], documents[-1][1], ingest_result_set, [simple_workflow_with_intents, result], {})
        catalog = catalog[-1]

        ensemble.append_catalog(catalog)
        ensemble_model.add_ensemble(ensemble, project_intents)
        qtbot.wait(1000)
        root = ensemble_model.index(0, 0, QModelIndex())
        ensemble_model.setData(root.child(0, 0), True, Qt.CheckStateRole)

    widget.setMinimumSize(800, 600)
    widget.show()
    qtbot.addWidget(widget)

    workflow_editor = WorkflowEditor(simple_workflow_with_intents, callback_slot=showResult)
    workflow_editor.run_workflow()

    qtbot.wait(7000)