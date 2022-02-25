from qtpy.QtCore import Qt, QModelIndex
from databroker.core import BlueskyRun
from qtpy.QtWidgets import QTreeView, QAbstractItemView, QMenu, QAction

from xicam.core.intents import Intent
from xicam.core.workspace import Ensemble
from xicam.gui.delegates.lineedit import LineEditDelegate


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

    def _create_ensemble_action(self, _):
        ensemble = Ensemble()
        # Note this ensemble has no catalogs; so we don't need projectors passed (just [])
        self.model().appendEnsemble(ensemble, [])

    def _set_active_action(self, _):
        # Update the model data with the currentIndex corresponding to where the user right-clicked
        # Update the active role based on the value of checked
        # self.model().setData(self.currentIndex(), checked, EnsembleModel.active_role)
        self.model().activeEnsemble = self.currentIndex().internalPointer()

    def customMenuRequested(self, position):
        """Builds a custom menu for items items"""
        index = self.indexAt(position)  # type: QModelIndex
        menu = QMenu(self)

        if index.isValid():

            data = index.internalPointer()
            if isinstance(data, Ensemble):

                # Allow renaming the ensemble via the context menu
                rename_action = QAction("Rename Collection", menu)
                rename_action.triggered.connect(self._rename_action)
                menu.addAction(rename_action)

                # Allow toggling the active ensemble via the context menu
                # * there can only be at most 1 active ensemble
                # * there are only 0 active ensembles when data has not yet been loaded ???
                # * opening data updates the active ensemble to that data
                is_active = bool(self.model().activeEnsemble == data)
                active_text = "Active"
                set_active_action = QAction(active_text, menu)
                if is_active is True:
                    set_active_action.setEnabled(False)
                else:
                    set_active_action.setEnabled(True)
                    set_active_action.setText(f"Set {active_text}")

                # Make sure to update the model with the active / deactivated ensemble
                set_active_action.triggered.connect(self._set_active_action)
                # Don't allow deactivating the active ensemble if there is only one loaded
                if self.model().rowCount() == 1 and self.model().activeEnsemble is not None:
                    set_active_action.setEnabled(False)
                # Allow setting an active ensemble when there is only one (e.g. an active ensemble is removed
                # TODO -- better active / removal management
                #   are active ensembles removable?
                #   if yes, which ensemble becomes active?
                #   should we allow no ensembles to be active?
                elif self.model().rowCount() == 1 and self.model().activeEnsemble is None:
                    set_active_action.setEnabled(True)
                menu.addAction(set_active_action)

                menu.addSeparator()

            remove_text = "Remove "
            if isinstance(data, Ensemble):
                remove_text += "Ensemble"
            elif isinstance(data, BlueskyRun):
                remove_text += "Catalog"
            elif isinstance(data, Intent):
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
