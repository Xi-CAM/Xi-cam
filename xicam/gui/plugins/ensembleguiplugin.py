import weakref

from qtpy.QtWidgets import QApplication, QWidget, QTextEdit, QGroupBox, QVBoxLayout
from qtpy.QtCore import Qt, QEvent, QObject
from databroker.core import BlueskyRun
from xicam.core.execution import Workflow

from xicam.gui.actions import Action
from xicam.gui.models import EnsembleModel, IntentsModel
from xicam.gui.widgets.linearworkfloweditor import WorkflowEditor
from xicam.gui.widgets.views import DataSelectorView, StackedCanvasView
from xicam.plugins import GUIPlugin, GUILayout


class EnsembleGUIPlugin(GUIPlugin):
    """GUI plugin that uses the Xi-CAM 'Ensemble' architecture for data organization.

    Attributes
    ----------
    canvases_view : StackedCanvasView
        Canvas view attached to the `intents_model`, visualizes data.
    ensemble_model : EnsembleModel
        Model that stores Ensembles.
    ensemble_view : DataSelectorView
        View attached to `ensemble_model` that controls visualizing data.
    intents_model : IntentsModel
        Model that stores visualizable data in the `ensemble_model` (i.e. Intents).
    gui_layout_template : dict
        Dict that includes `canvases_view`, `ensemble_view`, `workflow_editor`, and `xi_help`.
        Convenience as a template layout when creating GUILayouts for stages.
    workflow_editor : WorkflowEditor
        Workflow editor that contains empty Workflow; re-initialize for custom workflows.
    xi-help : HelpWidget
        Interactive helper widget.
    """
    name = "Ensemble Plugin"
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

        self.workflow_editor = WorkflowEditor(Workflow())

        self.xi_help = HelpWidget()

        self.gui_layout_template = {"center": self.canvases_view,
                                    "right": self.ensemble_view,
                                    "rightbottom": self.workflow_editor,
                                    "leftbottom": self.xi_help}

    def process_action(self, action: Action, canvas: "XicamIntentCanvas"):
        ...

    def appendCatalog(self, catalog: BlueskyRun, **kwargs):
        self.ensemble_model.append_to_ensemble(catalog, None, self._projectors)


class HelpTextDisplay(QTextEdit):
    def __init__(self, text: str = "", parent=None):
        super(HelpTextDisplay, self).__init__(text, parent)

        self.setContextMenuPolicy(Qt.NoContextMenu)
        self.setReadOnly(True)
        self.setPlaceholderText("(No help available for the widget at your current mouse location.)")

class HelpWidget(QGroupBox):
    """Widget that displays interactive help text.

    Installs an event filter on the application that can be used to get and display a widget's `whatsThis` text.
    """
    def __init__(self, title="Xi-Help Beta", parent=None):
        super(HelpWidget, self).__init__(title, parent)
        self.setObjectName(self.__class__.__name__)
        self.setWhatsThis("This widget displays any available help text "
                          "when you hover your mouse over a widget in Xi-CAM."
                          "Try it out!")

        QApplication.instance().installEventFilter(self)

        self._help_display = HelpTextDisplay()
        layout = QVBoxLayout()
        layout.addWidget(self._help_display)
        self.setLayout(layout)

        # Stores a weakref to a previously entered widget
        self._cached_entered_widget = lambda: None  # type: weakref.ref

    # FIXME: better (shorter) name; want to convey this information so it isn't confusing when revisiting.
    def _is_child_of_previously_entered_widget_with_help_text(self, widget: QWidget) -> bool:
        """Checks if the cached entered widget is an ancestor of the passed widget.

        Supports maintaining the help text of an entered widget when its children do not have help text.
        Since we are checking if the cached widget is an ancestor of the widget being left (w/ Leave event),
        we don't have to manage releasing the cached widget ref (to a duck-typed lambda: None).
        """
        entered_widget = self._cached_entered_widget()
        if entered_widget is not None:
            return entered_widget.isAncestorOf(widget)
        return False


    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        """Event filter to process an event for the given destination.

        In this case, this widget listens for Enter events on the application level
        (during this widget's init, this eventFilter is installed on the app instance).

        When the destination object is a QWidget,
        we can try to update this widget's help_text with the destination widget's what's this help text.
        If there is no what's this text, we set the help_text back to its placeholderText.
        """
        if event.type() == QEvent.Enter:
            if isinstance(obj, QWidget):
                help_text = obj.whatsThis()
                # When the obj has help text, let's update the help text widget
                if help_text != "":
                    self._help_display.setText(help_text)
                    # Store a ref to the entered widget so we can maintain the help text if its children don't have any
                    self._cached_entered_widget = weakref.ref(obj)

        if event.type() == QEvent.Leave:
            if isinstance(obj, QWidget):
                # When we leave a widget, if it didn't have help text,
                # we want to check if the previously cached (entered) widget is its ancestor.
                # This will maintain the ancestor's help text in the help text widget when the child has not help text.
                if obj.whatsThis() == "":
                    # Revert to placeholder text when we have left a widget and the cached widget is not its ancestor
                    # (i.e. the previously entered widget with help text is not related).
                    if not self._is_child_of_previously_entered_widget_with_help_text(obj):
                        self._help_display.setText(self._help_display.placeholderText())

        return super(HelpWidget, self).eventFilter(obj, event)
                
