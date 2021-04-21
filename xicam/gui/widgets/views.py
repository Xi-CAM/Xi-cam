import itertools
import sys

from qtpy.QtCore import Signal, QModelIndex, QPoint, Qt, QAbstractItemModel
from qtpy.QtGui import QIcon, QMouseEvent, QPainter, QBrush, QFont
from qtpy.QtWidgets import QAbstractItemView, QApplication, QButtonGroup, QHBoxLayout, QPushButton, \
    QSplitter, QStackedWidget, QStyleFactory, QTabWidget, QTreeView, QVBoxLayout, QWidget, QStyledItemDelegate, \
    QStyleOptionViewItem, QLineEdit, QStyle, QAction, QMenu
from xicam.core.workspace import WorkspaceDataType, Ensemble
from xicam.gui.canvases import XicamIntentCanvas
from xicam.gui.actions import Action

from xicam.gui.static import path
from xicam.gui.canvasmanager import XicamCanvasManager
from xicam.gui.models import EnsembleModel
from xicam.core import msg


class CanvasView(QAbstractItemView):
    """Defines a Qt-view interface for rendering and unrendering canvases."""

    sigInteractiveAction = Signal(Action, XicamIntentCanvas)
    sigTest = Signal(object)

    def __init__(self, parent=None, icon=QIcon()):
        super(CanvasView, self).__init__(parent)
        self._canvas_manager = XicamCanvasManager()
        self.icon = icon

        self._last_seen_intents = set()

        self.setWhatsThis(
            "This area will display any items that are checked in the data selector view (the widget on the right)."
        )

    def refresh(self):
        for i in range(self.model().rowCount()):
            self.model().setData(self.model().index(i,0), None, role=EnsembleModel.canvas_role)
        self.dataChanged(self.model().index(0,0), self.model().index(self.model().rowCount(),0), roles=[EnsembleModel.canvas_role])

    def render(self, intent, canvas):
        item = canvas.render(intent)

    def unrender(self, intent, canvas):
        # TODO: how do we feed the return val back to the canvas manager?
        canvas.unrender(intent)
        # if canvas_removable:
        #     self.canvases.remove(canvas)
        #return canvas_removable

    def dataChanged(self, topLeft: QModelIndex, bottomRight: QModelIndex, roles=None):
        """
        Listens for dataChanged on an Intent (TreeItem)'s check state.

        Renders/unrenders according to the check state.
        Then, defers showing canvases to any derived views (e.g. StackedCanvasView).
        """
        # We only care about the check state changing here (whether to render or unrender)
        if Qt.CheckStateRole in roles or EnsembleModel.canvas_role in roles:

            intent_row_start = topLeft.row()
            intent_row_stop = bottomRight.row()

            new_intents = set()

            if topLeft.isValid() and bottomRight.isValid():
                for row in range(intent_row_start, intent_row_stop+1):
                    intent_index = self.model().index(row, 0)
                    intent = intent_index.internalPointer().data(EnsembleModel.object_role)
                    try:
                        canvas = self._canvas_manager.canvas_from_index(intent_index.internalPointer())
                        try:
                            canvas.sigInteractiveAction.connect(self.sigInteractiveAction, type=Qt.UniqueConnection)
                        except TypeError:  # ignore errors from connection already being established
                            pass
                    except Exception as ex:
                        msg.logMessage(f'A error occurred displaying the intent named {intent.name}:', level=msg.ERROR)
                        msg.logError(ex)
                    else:
                        new_intents.add((canvas, intent))

            removed_intents = self._last_seen_intents - new_intents
            added_intents = new_intents - self._last_seen_intents

            for canvas, intent in removed_intents:
                if canvas is not None:
                    self.unrender(intent, canvas)

            for canvas, intent in added_intents:
                if canvas is not None:
                    self.render(intent, canvas)

            self._last_seen_intents = new_intents

            self.show_canvases()

    def horizontalOffset(self):
        return 0

    def indexAt(self, point: QPoint):
        return QModelIndex()

    def moveCursor(
            self,
            QAbstractItemView_CursorAction,
            Union,
            Qt_KeyboardModifiers=None,
            Qt_KeyboardModifier=None,
    ):
        return QModelIndex()

    def rowsInserted(self, index: QModelIndex, start, end):
        return

    def rowsAboutToBeRemoved(self, parent_index: QModelIndex, start, end):
        """Refresh/close any canvases whose items are being removed."""
        ... # NOT BEING USED CURRENTLY

    def scrollTo(self, QModelIndex, hint=None):
        return

    def verticalOffset(self):
        return 0

    def visualRect(self, QModelIndex):
        from qtpy.QtCore import QRect

        return QRect()

    def show_canvases(self):
        """Polymorphically defers to derived views (e.g. StackedCanvasView)"""
        ...


class CanvasDisplayWidget(QWidget):
    """Defines a simple interface for widgets that can display canvases."""
    def __init__(self, parent=None):
        super(CanvasDisplayWidget, self).__init__(parent)

        self.setWhatsThis(
            "This area will display any items that are checked in the data selector view (the widget on the right)."
        )

    def clear_canvases(self):
        """Clear all canvases from the widget."""
        ...

    def show_canvases(self, canvases):
        """Display the passed canvases."""
        ...

#TODO:
    # [ ] commit changes
    # [x] fix show canvases
    # [ ] check with nxs file
    # [ ] add setModel to StackedCanvasView class


class StackedCanvasView(CanvasView):
    """
    View that can display intents in their corresponding canvases.

    Currently, uses a stacked widget with several pages:
    one for tabview and others for different split views.

    Can be adapted as long as its internal widgets are CanvasDisplayWidgets.
    """
    def __init__(self, parent=None, model=None):
        super(StackedCanvasView, self).__init__(parent)
        if model is not None:
            self.setModel(model)

        self.canvas_display_widgets = [
            CanvasDisplayTabWidget(),
            SplitHorizontal(),
            SplitVertical(),
            SplitThreeView(),
            SplitGridView()
        ]

        ### Create stacked widget and fill pages with different canvas display widgets
        self.stackedwidget = QStackedWidget(self)
        # Create a visual layout section for the buttons that are used to switch the widgets
        self.buttonpanel = QHBoxLayout()
        self.buttonpanel.addStretch(10)
        # Create a logical button grouping that will:
        #   - show the currently selected view (button will be checked/pressed)
        #   - allow for switching the buttons/views in a mutually exclusive manner (only one can be pressed at a time)
        self.buttongroup = QButtonGroup()

        def add_canvas_display_widgets():
            for i in range(len(self.canvas_display_widgets)):
                # Add the view to the stacked widget
                self.stackedwidget.addWidget(self.canvas_display_widgets[i])
                # Create a button, using the view's recommended display icon
                button = QPushButton(self)
                button.setCheckable(True)
                button.setIcon(self.canvas_display_widgets[i].icon)
                button.setToolTip(getattr(self.canvas_display_widgets[i], "tool_tip", None))
                button.setWhatsThis(getattr(self.canvas_display_widgets[i], "whats_this", None))
                # Add the button to the logical button group
                self.buttongroup.addButton(button, i)
                # Add the button to the visual layout section
                self.buttonpanel.addWidget(button)

        add_canvas_display_widgets()

        def set_default_canvas_display_widget():
            # The first button added to the buttongroup will be the currently selected button (and therefore view)
            self.buttongroup.button(0).setChecked(True)

        set_default_canvas_display_widget()

        # Whenever a button is switched, capture its id (corresponds to integer index in our case);
        # this will handle switching the view and displaying canvases.
        self.buttongroup.idToggled.connect(self.switch_view)

        # define outer layout & add stacked widget and button panel
        self.layout = QVBoxLayout()
        self.layout.addWidget(self.stackedwidget)
        self.layout.addLayout(self.buttonpanel)
        self.setLayout(self.layout)

    # INTERFACING WITH TOOLBAR (see XPCSToolbar)
    def view(self):
        # from xicam.gui.canvases import ImageIntentCanvas
        view = self.stackedwidget.currentWidget()
        return view.getView()
        # return None
    # DONE INTERFACING

    def switch_view(self, id, toggled):
        # when toggled==True, the the button is the new button that was switched to.
        # when False, the button is the previous button
        view = self.canvas_display_widgets[id]
        if not toggled:
            ...
            # TODO: is there anything we need to do here (re: cleanup)?

        else:
            self.stackedwidget.setCurrentIndex(id)
            self.show_canvases()

    def show_canvases(self):
        self.stackedwidget.currentWidget().clear_canvases()
        self.stackedwidget.currentWidget().show_canvases(self._canvas_manager.canvases(self.model()))


class CanvasDisplayTabWidget(CanvasDisplayWidget):
    """Canvas display widget that displays canvases in tabs."""

    def __init__(self, parent=None):
        super(CanvasDisplayTabWidget, self).__init__(parent)

        self._tabWidget = QTabWidget()
        self._tabWidget.setParent(self)

        self.setLayout(QVBoxLayout())
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().addWidget(self._tabWidget)

        # Set attrs for when the buttons are created
        self.icon = QIcon(path('icons/tabs.png'))
        # TODO: right now, we are not attaching help text directly to this widget
        #   (it can be confusing when trying to hover over the StackedCanvasView,
        #   the StackedCanvasView's help text is hard to display)
        self.tool_tip = "Tab View"
        self.whats_this = "Reorganizes displayed data into separate tabs."

    def getView(self):
        return self._tabWidget.currentWidget()

    def clear_canvases(self):
        self._tabWidget.clear()

    def show_canvases(self, canvases):
        self._tabWidget.clear()
        for canvas in canvases:
            if canvas is not None:
                self._tabWidget.addTab(canvas, canvas.canvas_name)


class SplitView(CanvasDisplayWidget):
    """
    Displaying results in a (dynamic) split view.
    """

    def __init__(
        self,
        parent: QWidget = None
    ):
        super(SplitView, self).__init__(parent)
        # self.outer_splitter = QSplitter()
        # self.inner_splitter = QSplitter()
        self.layout = QHBoxLayout()

        self.max_canvases = 0

# TODO [ ] add note/hint if to few/many dataset selected
#      [ ] label dataset in view


class SplitHorizontal(SplitView):
    """ Displays data in wide view, 2 on top of each other with a horizontal, movable divider bar"""
    def __init__(self, *args, **kwargs):
        super(SplitHorizontal, self).__init__(*args, **kwargs)

        self.splitter = QSplitter(Qt.Vertical)
        self.splitter.setSizes([100, 200])

        self.layout.addWidget(self.splitter)
        self.setLayout(self.layout)
        QApplication.setStyle(QStyleFactory.create('Cleanlooks'))
        self.setGeometry(300, 300, 300, 200)

        self.max_canvases = 2

        # Set attrs for when the buttons are created
        self.icon = QIcon(path('icons/1x1hor.png'))
        self.tool_tip = "Horizontal Split View"
        self.whats_this = "Displays up to two visualized data items in a horizontal layout."

    def clear_canvases(self):
        for i in reversed(range(self.splitter.count())):
            widget = self.splitter.widget(i)
            widget.setParent(None)

    def show_canvases(self, canvases):
        for canvas in itertools.islice(canvases, self.max_canvases):
            if canvas is not None:
                self.splitter.addWidget(canvas)
                canvas.setVisible(True)


class SplitVertical(SplitHorizontal):
    """ Displays data in vertical view, 2 next to each other with a vertical, movable divider bar"""
    def __init__(self, *args, **kwargs):
        super(SplitVertical, self).__init__(*args, **kwargs)

        self.splitter.setOrientation(Qt.Horizontal)

        # Set attrs for when the buttons are created
        self.icon = QIcon(path('icons/1x1vert.png'))
        self.tool_tip = "Vertical Split View"
        self.whats_this = "Displays up to two visualized data items in a vertical layout."


class SplitThreeView(SplitView):
    """ Shows 3 data displays: 2 next to each other with a vertical, movable divider bar
        and a third one below these in wide view with a horizontal, movable divider bar
    """
    def __init__(self, *args, **kwargs):
        super(SplitThreeView, self).__init__(*args, **kwargs)

        self.top_splitter = QSplitter(Qt.Horizontal)
        self.top_splitter.setSizes([100, 200])

        self.outer_splitter = QSplitter(Qt.Vertical)
        self.outer_splitter.insertWidget(0, self.top_splitter)

        self.layout.addWidget(self.outer_splitter)
        self.setLayout(self.layout)
        QApplication.setStyle(QStyleFactory.create('Cleanlooks'))
        self.setGeometry(300, 300, 300, 200)

        self.max_canvases = 3

        # Set attrs for when the buttons are created
        self.icon = QIcon(path('icons/2x1grid.png'))
        self.tool_tip = "3-Way Split View"
        self.whats_this = "Displays up to three visualized data items."

    def clear_canvases(self):
        for splitter in [self.top_splitter, self.outer_splitter]:
            for i in reversed(range(splitter.count())):
                widget = splitter.widget(i)
                if widget is not self.top_splitter:  # Don't prune the embedded splitter
                    widget.setParent(None)

    def show_canvases(self, canvases):
        for i, canvas in itertools.islice(enumerate(canvases), self.max_canvases):
            if canvas is not None and i < self.max_canvases:
                if i < 2:
                    self.top_splitter.addWidget(canvas)

                else:
                    self.outer_splitter.addWidget(canvas)
                canvas.setVisible(True)


class SplitGridView(SplitView):
    def __init__(self, *args, **kwargs):
        super(SplitGridView, self).__init__(*args, **kwargs)

        self.top_splitter = QSplitter(Qt.Horizontal)
        self.top_splitter.setSizes([100, 200])

        self.bottom_splitter = QSplitter(Qt.Horizontal)
        self.bottom_splitter.setSizes([100, 200])

        # connect splitter1 and splitter2 to move together
        # TODO which version is desired? connect splitter or free moving?
        # self.top_splitter.splitterMoved.connect(self.moveSplitter)
        # self.bottom_splitter.splitterMoved.connect(self.moveSplitter)
        # self._spltA = self.top_splitter
        # self._spltB = self.bottom_splitter

        self.outer_splitter = QSplitter(Qt.Vertical)
        self.outer_splitter.insertWidget(0, self.top_splitter)
        self.outer_splitter.insertWidget(1, self.bottom_splitter)
        self.outer_splitter.setSizes([200, 400])

        self.layout.addWidget(self.outer_splitter)
        self.setLayout(self.layout)
        QApplication.setStyle(QStyleFactory.create('Cleanlooks'))
        self.setGeometry(300, 300, 300, 200)

        self.max_canvases = 4

        # Set attrs for when the buttons are created
        self.icon = QIcon(path('icons/2x2grid.png'))
        self.tool_tip = "2x2 Grid View"
        self.whats_this = "Displays up to four visualized data items in a grid layout."

    def moveSplitter( self, index, pos):
        splt = self._spltA if self.sender() == self._spltB else self._spltB
        splt.blockSignals(True)
        splt.moveSplitter(index, pos)
        splt.blockSignals(False)

    def show_canvases(self, canvases):
        for splitter in [self.top_splitter, self.bottom_splitter]:
            for i in reversed(range(splitter.count())):
                widget = splitter.widget(i)
                widget.setParent(None)

        for canvas in itertools.islice(canvases, 2):
            self.top_splitter.addWidget(canvas)
            canvas.setVisible(True)

        for canvas in itertools.islice(canvases, 2):
            self.bottom_splitter.addWidget(canvas)
            canvas.setVisible(True)


class LineEditDelegate(QStyledItemDelegate):
    """Custom editing delegate that allows renaming text and updating placeholder text in a line edit.

    This class was written for using with the DataSelectorView.
    """
    def __init__(self, parent=None):
        super(LineEditDelegate, self).__init__(parent)
        self._default_text = "Untitled"

    def createEditor(self, parent: QWidget,
                     option: QStyleOptionViewItem,
                     index: QModelIndex) -> QWidget:
        editor = QLineEdit(parent)
        editor.setPlaceholderText(self._default_text)
        editor.setFrame(False)
        return editor

    def setEditorData(self, editor: QWidget, index: QModelIndex):
        value = index.model().data(index, Qt.DisplayRole)
        editor.setText(value)

    def setModelData(self, editor: QWidget,
                     model: QAbstractItemModel,
                     index: QModelIndex):

        text = editor.text()
        if text == "":
            text = editor.placeholderText()
        # Update the "default" text to the previous value edited in
        self._default_text = text
        model.setData(index, text, Qt.DisplayRole)

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex):
        super(LineEditDelegate, self).paint(painter, option, index)
        return

        # if index.data(role=EnsembleModel.active_role):
        #     active_brush = QBrush(Qt.cyan)
        #     painter.save()
        #     painter.fillRect(option.rect, active_brush)
        #     painter.restore()
        #
        # super(LineEditDelegate, self).paint(painter, option, index)


class DataSelectorView(QTreeView):
    def __init__(self, parent=None):
        super(DataSelectorView, self).__init__(parent)

        # We are implementing our own custom context menu
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.customMenuRequested)

        # Don't allow double-clicking for expanding; use it for editing
        self.setExpandsOnDoubleClick(False)
        self.setEditTriggers(QAbstractItemView.DoubleClicked)

        # Attach a custom delegate for the editing
        delegate = LineEditDelegate(self)
        self.setItemDelegate(delegate)

        self.setDragEnabled(True)

        self.setAnimated(True)

        self.setWhatsThis("This widget helps organize and display any loaded data or data created within Xi-CAM. "
                          "Data is displayed in a tree-like manner:\n"
                          "  Collection\n"
                          "    Catalog\n"
                          "      Visualizable Data\n"
                          "Click on the items' checkboxes to visualize them.\n"
                          "Right-click a Collection to rename it.\n"
                          "Right-click in empty space to create a new Collection.\n")

    def setModel(self, model):
        try:
            self.model().rowsInserted.disconnect(self._expand_rows)
        except Exception:
            ...
        super(DataSelectorView, self).setModel(model)
        self.model().rowsInserted.connect(self._expand_rows)

    def _expand_rows(self, parent: QModelIndex, first: int, last: int):
        self.expandRecursively(parent)

    def _rename_action(self, _):
        # Request editor (see the delegate created in the constructor) to change the ensemble's name
        self.edit(self.currentIndex())

    def _remove_action(self, _):
        index = self.currentIndex()  # QModelIndex
        removed = self.model().removeRow(index.row(), index.parent())
        # self.model().dataChanged.emit(QModelIndex(), QModelIndex())
        ...

    def _create_ensemble_action(self, _):
        ensemble = Ensemble()
        # Note this ensemble has no catalogs; so we don't need projectors passed (just [])
        self.model().add_ensemble(ensemble, [], active=True)

    def _set_active_action(self, checked: bool):
        # Update the model data with the currentIndex corresponding to where the user right-clicked
        # Update the active role based on the value of checked
        self.model().setData(self.currentIndex(), checked, EnsembleModel.active_role)

    def customMenuRequested(self, position):
        """Builds a custom menu for items items"""
        index = self.indexAt(position)  # type: QModelIndex
        menu = QMenu(self)

        if index.isValid():

            if index.data(EnsembleModel.data_type_role) == WorkspaceDataType.Ensemble:

                # Allow renaming the ensemble via the context menu
                rename_action = QAction("Rename Collection", menu)
                rename_action.triggered.connect(self._rename_action)
                menu.addAction(rename_action)

                # Allow toggling the active ensemble via the context menu
                # * there can only be at most 1 active ensemble
                # * there are only 0 active ensembles when data has not yet been loaded ???
                # * opening data updates the active ensemble to that data
                is_active = index.data(EnsembleModel.active_role)
                active_text = "Active"
                toggle_active_action = QAction(active_text, menu)
                toggle_active_action.setCheckable(True)
                if is_active is True:
                    toggle_active_action.setChecked(True)
                else:
                    toggle_active_action.setChecked(False)
                    toggle_active_action.setText(f"Not {active_text}")

                # Make sure to update the model with the active / deactivated ensemble
                toggle_active_action.toggled.connect(self._set_active_action)
                # Don't allow deactivating the active ensemble if there is only one loaded
                if self.model().rowCount() == 1:
                    toggle_active_action.setEnabled(False)
                menu.addAction(toggle_active_action)

                menu.addSeparator()

            remove_text = "Remove "
            data_type_role = index.data(EnsembleModel.data_type_role)
            if data_type_role == WorkspaceDataType.Ensemble:
                remove_text += "Ensemble"
            elif data_type_role == WorkspaceDataType.Catalog:
                remove_text += "Catalog"
            elif data_type_role == WorkspaceDataType.Intent:
                remove_text += "Item"
            remove_action = QAction(remove_text, menu)
            remove_action.triggered.connect(self._remove_action)
            menu.addAction(remove_action)

        else:
            create_ensemble_action = QAction("Create New Collection", menu)
            create_ensemble_action.triggered.connect(self._create_ensemble_action)
            menu.addAction(create_ensemble_action)

        # Display menu wherever the user right-clicked
        menu.popup(self.viewport().mapToGlobal(position))


def main():
    app = QApplication(sys.argv)
    ex = StackedCanvasView()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
