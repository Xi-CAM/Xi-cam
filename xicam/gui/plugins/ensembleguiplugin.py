from databroker.core import BlueskyRun

from xicam.core.workspace import Ensemble
from xicam.gui.actions import Action
from xicam.gui.models import EnsembleModel, IntentsModel
from xicam.gui.widgets.views import DataSelectorView, StackedCanvasView
from xicam.plugins import GUIPlugin


class EnsembleGUIPlugin(GUIPlugin):
    """GUI plugin that uses the Xi-CAM 'Ensemble' architecture for data organization.

    Includes an EnsembleModel, DataSelectorView, IntentsModel, and CanvasView.

    Ensemble architecture is defined primarily by an EnsembleModel class.
    This stores data in a Qt-based tree-like model, where each ensemble
    encapsulates one or more catalogs, each of which may contain Intents
    for how to visualize the data.

    """
    supports_ensembles = True

    def __init__(self, *args, **kwargs):
        super(EnsembleGUIPlugin, self).__init__(*args, **kwargs)

        self._projectors = []  # List[Callable[[BlueskyRun], List[Intent]]]
        self.ensemble_model = EnsembleModel()

        self.intents_model = IntentsModel()
        self.intents_model.setSourceModel(self.ensemble_model)

        self.ensemble_view = DataSelectorView()
        self.ensemble_view.setModel(self.ensemble_model)

        self.canvases_view = StackedCanvasView()
        self.canvases_view.setModel(self.intents_model)

        self.canvases_view.sigInteractiveAction.connect(self.process_action)
        self.canvases_view.sigTest.connect(self._test)

    def _test(self, o):
        print("EnsembleGUIPlugin._test")

    def process_action(self, action: Action, canvas: "XicamIntentCanvas"):
        print("EnsembleGUIPlugin.process_action")
        ...

    def appendCatalog(self, catalog: BlueskyRun, **kwargs):
        append = True
        active_ensemble = self.ensemble_model.active_ensemble
        if active_ensemble is not None:
            ensemble = active_ensemble.data(EnsembleModel.object_role)
        else:
            # FIXME who controls creating a new vs appending to existing ensemble?
            ensemble = Ensemble()
        ensemble.append_catalog(catalog)

        if not append:
            self.ensemble_model.add_ensemble(ensemble, self._projectors)
        else:
            self.ensemble_model.append_to_ensemble(catalog, ensemble, self._projectors)
