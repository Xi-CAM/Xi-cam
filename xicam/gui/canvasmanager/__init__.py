from typing import Generator

from PyQt5.QtCore import QModelIndex
from xicam.core.intents import Intent
from xicam.core.workspace import WorkspaceDataType
from xicam.gui.models import IntentsModel, EnsembleModel, TreeModel
from xicam.plugins import manager as pluginmanager
from xicam.plugins.intentcanvasplugin import IntentCanvas


class CanvasManager:
    def __init__(self):
        ...

    def canvas_from_intent(self, intent):
        ...

    def drop_canvas(self, key):
        ...

    # def render(self, canvas, intent):
    #     canvas.render(intent)

    def canvas_from_registry(self, canvas_name, registry):
        ...

    # ImageIntentCanvas <- ImageWithRoiIntentCanvas
    # or (preferred) add logic in the ImageIntentCanvas render method


class XicamCanvasManager(CanvasManager):
    def __init__(self):
        super(XicamCanvasManager, self).__init__()

    def canvases(self, model: IntentsModel) -> Generator[IntentCanvas, None, None]:
        """Retrieve all canvases from a given model."""
        # Create a mapping from canvas to rows to get unique canvas references.
        seen_canvases = set()

        for row in range(model.rowCount()):
            canvas = self.canvas_from_row(row, model)
            if canvas not in seen_canvases:
                seen_canvases.add(canvas)
                yield canvas

    def canvas_from_registry(self, canvas_class_name, registry, canvas_name):
        return registry.get_plugin_by_name(canvas_class_name, "IntentCanvasPlugin")(canvas_name=canvas_name)

    def drop_canvas(self, key: QModelIndex):
        intent = key.data(EnsembleModel.object_role)
        canvas = key.data(EnsembleModel.canvas_role)
        if canvas:
            drop_completely = canvas.unrender(intent)

    def canvas_from_row(self, row: int, model, parent_index=QModelIndex()):
        # TODO: model.index v. model.sourceModel().index (i.e. should this only be Proxy Model, or EnsembleModel, or both)?
        return self.canvas_from_index(model.index(row, 0, parent_index).internalPointer())

    def canvas_from_index(self, index: QModelIndex):
        if not index.isValid():
            return None

        if index.data(EnsembleModel.data_type_role) != WorkspaceDataType.Intent:
            print(f'WARNING: canvas_from_index index {index} is not an intent')
            return None

        # Canvas exists for index, return
        # TODO: in tab view, with multiple intents selected (e.g. 2 rows checked),
        #       non-0 row intents (every intent except first) does not have a valid object in canvas_role
        canvas = index.model().data(index, EnsembleModel.canvas_role)
        if canvas:
            return canvas

        # There is another canvas we know about we should use
        for match_index in self.all_intent_indexes(index.model()):
            if self.is_matching_canvas_type(index, match_index):
                canvas = match_index.model().data(match_index, EnsembleModel.canvas_role)
                if canvas is not None:
                    index.model().setData(index, canvas, EnsembleModel.canvas_role)
                    return canvas

        # Does not exist, create new canvas and return
        intent = index.model().data(index, EnsembleModel.object_role)
        canvas_class_name = intent.canvas
        registry = pluginmanager
        canvas = self.canvas_from_registry(canvas_class_name, registry, intent.canvas_name)

        index.model().setData(index, canvas, EnsembleModel.canvas_role)
        return canvas

    @classmethod
    def all_intent_indexes(cls, model: TreeModel, parent_index=QModelIndex()):

        for row in range(model.rowCount(parent_index)):
            child_index = model.index(row, 0, parent_index)
            data_type = model.data(child_index, EnsembleModel.data_type_role)
            if data_type is WorkspaceDataType.Intent:
                yield child_index
            elif model.hasChildren(child_index):
                yield from cls.all_intent_indexes(model, child_index)

    def is_matching_canvas_type(self, index: QModelIndex, match_index: QModelIndex):
        match_intent = match_index.data(EnsembleModel.object_role)
        intent = index.data(EnsembleModel.object_role)
        if not isinstance(intent, Intent):
            print(f"WARNING: during matching, index {index.data} is not an Intent")
            return False
        if not isinstance(match_intent, Intent):
            print(f"WARNING: during matching, match_index {index.data} is not an Intent")
            return False
        # assert isinstance(intent, Intent)
        # assert isinstance(match_intent, Intent)

        match_canvas_type_string = match_intent.canvas
        intent_canvas_type_string = intent.canvas

        if intent_canvas_type_string != match_canvas_type_string:
            return False

        # By definition, if a match_key is not provided, the intent is un-matchable
        if intent.match_key is None or match_intent.match_key is None:
            return False

        if intent.match_key != match_intent.match_key:
            return False

        return True