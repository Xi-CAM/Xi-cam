# Modification of David Zuber's MenuView at https://github.com/storax/qmenuview and on PyPi
# Changes:
# - Uses qtpy instead of PySide

# Copyright (c) 2015, David Zuber
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without modification, are permitted provided that the following conditions are met:
#
# * Redistributions of source code must retain the above copyright notice, this list of conditions and the following disclaimer.
#
# * Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the following disclaimer in the documentation and/or other materials provided with the distribution.
#
# * Neither the name of Pyside QMenuView nor the names of its contributors may be used to endorse or promote products derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.


import functools

from qtpy import QtCore, QtGui, QtWidgets

__all__ = ["MenuView", "SetDataArgs"]


class MenuView(QtWidgets.QMenu):
    """A view that creates submenus based on a model.
    The model can be a list, table or treemodel.
    Each row equals to one submenu/action.
    In a treemodel, the leaves are plain actions, the rest also have menus on top.
    The view listens to the following signals:
      - :data:`PySide.QtCore.QAbstractItemModel.modelReset`
      - :data:`PySide.QtCore.QAbstractItemModel.rowsInserted`
      - :data:`PySide.QtCore.QAbstractItemModel.rowsAboutToBeRemoved`
      - :data:`PySide.QtCore.QAbstractItemModel.dataChanged`
    So the view is quite dynamic. If all child rows of an index are removed,
    the menu gets removed from the action. If rows are inserted to a parent index,
    which had no children, the action will get a menu.
    If an action emits a signal, the view will emit a signal too.
    The signal will contain the index and any arguments of the action's signal.
    You can get the action by using :meth:`MenuView.get_action`.
    See :data:`MenuView.action_triggered`, :data:`MenuView.action_hovered`,
    :data:`MenuView.action_toggled`.
    .. Note:: At the moment :data:`PySide.QtGui.QAction.changed` will not be handled.
              There currently is a bug in :meth:`MenuView._get_parents`, which
              causes an infinite loop.
    You can set which column to use for each attribute. See :data:`MenuView.text_column`,
    :data:`MenuView.icon_column`, :data:`MenuView.icontext_column`,
    :data:`MenuView.tooltip_column`, :data:`MenuView.checked_column`,
    :data:`MenuView.whatsthis_column`, :data:`MenuView.statustip_column`.
    For more control on how the data gets applied to the action, change
    :data:`MenuView.setdataargs`. It is a list of :class:`SetDataArgs` containers.
    One container defines the functionname to use for setting the attribute,
    the column to use, the :data:`PySide.QtCore.Qt.ItemDataRole`, and a data conversion function.
    If you want custom menu and action classes,
    override :meth:`MenuView.create_menu`, :meth:`MenuView.create_action`.
    """

    action_hovered = QtCore.Signal(QtCore.QModelIndex)
    """Signal for when an action gets hovered"""
    action_triggered = QtCore.Signal(QtCore.QModelIndex, bool)
    """Signal for when an action gets triggered"""
    action_toggled = QtCore.Signal(QtCore.QModelIndex, bool)
    """Signal for when an action gets toggled"""

    def __init__(self, title="", parent=None):
        """Initialize a new menu view with the given title
        :param title: title of the top menu
        :type title: :class:`str`
        :param parent: the parent widget
        :type parent: :class:`PySide.QtGui.QWidget`
        :raises: None
        """
        super(MenuView, self).__init__(title, parent)
        self.text_column = 0
        """The column for the action text. Default 0"""
        self.icon_column = 0
        """The column for the action icon. Default 0"""
        self.icontext_column = -1
        """The column for the action icon text. Default -1"""
        self.tooltip_column = 0
        """The column for the tooltip data. Default 0"""
        self.checked_column = 0
        """The column for the checked data. Has to be checkable. Default 0"""
        self.whatsthis_column = 0
        """The column for the whatsThis text. Default 0"""
        self.statustip_column = 0
        """The column for the statustip text. Default 0"""
        self._model = None

        Qt = QtCore.Qt
        args = [
            SetDataArgs("setText", "text_column", Qt.DisplayRole, str),
            SetDataArgs("setIcon", "icon_column", Qt.DecorationRole, self._process_icondata),
            SetDataArgs("setIconText", "icontext_column", Qt.DisplayRole, str),
            SetDataArgs("setToolTip", "tooltip_column", Qt.ToolTipRole, str),
            SetDataArgs("setChecked", "checked_column", Qt.CheckStateRole, self._checkconvertfunc),
            SetDataArgs("setWhatsThis", "whatsthis_column", Qt.WhatsThisRole, str),
            SetDataArgs("setStatusTip", "statustip_column", Qt.StatusTipRole, str),
        ]
        self.setdataargs = args
        """A list of :class:`SetDataArgs` containers. Defines how the
        data from the model is applied to the action"""

    @property
    def model(self,):
        """Get the model
        :returns: the current model
        :rtype: :class:`PySide.QtCore.QAbstractItemModel`
        :raises: None
        """
        return self._model

    @model.setter
    def model(self, model):
        """Set the model
        :param model: the model to set
        :type model: :class:`PySide.QtCore.QAbstractItemModel`
        :returns: None
        :rtype: None
        :raises: None
        """
        signalmap = {
            "modelReset": self.reset,
            "rowsInserted": self.insert_menus,
            "rowsAboutToBeRemoved": self.remove_menus,
            "dataChanged": self.update_menus,
        }
        if self._model:
            for signal, callback in signalmap.items():
                getattr(self._model, signal).disconnect(callback)
        self._model = model
        if model:
            for signal, callback in signalmap.items():
                getattr(model, signal).connect(callback)

        self.action_toggled.connect(functools.partial(self._model.setData, role=QtCore.Qt.CheckStateRole))
        self.reset()

    def reset(self,):
        """Delete and recreate all menus
        :returns: None
        :rtype: None
        :raises: None
        """
        self.clear()
        self.create_all_menus()

    def create_all_menus(self,):
        """Create all menus according to the model
        :returns: None
        :rtype: None
        :raises: None
        """
        m = self._model
        if not m:
            return
        indizes = self._flatten_hierarchy(m)
        for i in indizes:
            self.create_menu_for_index(i)

    @staticmethod
    def _flatten_hierarchy(model, parent=None):
        """Return a level-order list of indizes
        :param model: the model to traverse
        :type model: :class:`PySide.QtCore.QAbstractItemModel`
        :param parent: the parent index. Default is the root.
        :type parent: :class:`PySide.QtCore.QModelIndex`
        :returns: a level-order list of indizes
        :rtype: :class:`list` of :class:`PySide.QtCore.QModelIndex`
        :raises: None
        """
        indizes = []
        if parent is None:
            parent = QtCore.QModelIndex()
        parents = [parent]
        children = []
        # for all parents, get the children
        # during the next iteration, the children become the parents
        # and are queried for children as well. Once no new children are found
        # the loop ends
        while parents:
            for parent in parents:
                for i in range(model.rowCount(parent)):
                    index = model.index(i, 0, parent)
                    indizes.append(index)
                    children.append(index)
            parents = children
            children = []
        return indizes

    def create_menu_for_index(self, index):
        m = self._model
        parentaction = self.get_action(index.parent())
        # Action has no menu yet. In order to create a sub action,
        # we have to convert it.
        if parentaction.menu() is None:
            self._convert_action_to_menu(parentaction)
        parent = parentaction.menu()
        beforeindex = index.sibling(index.row(), 0)
        before = self.get_action(beforeindex)
        if m.hasChildren(index):
            action = self.create_menu(parent)
        else:
            action = self.create_action(parent)
        parent.insertAction(before, action)
        self.set_action_data(action, index)
        signalmap = {
            action.triggered: self._action_triggered,
            action.hovered: self._action_hovered,
            action.toggled: self._action_toggled,
        }
        for signal, callback in signalmap.items():
            signal.connect(functools.partial(callback, action))

    def _convert_action_to_menu(self, action):
        parent = action.parentWidget()
        menuaction = self.create_menu(parent)
        action.setMenu(menuaction.menu())

    def create_menu(self, parent):
        """Create a menu and return the menus action.
        The parent of the menu has to be set to ``parent``
        :param parent: The parent menu
        :type parent: :class:`PySide.QtGui.QMenu`
        :returns: The menu action
        :rtype: :class:`PySide.QtGui.QAction`
        :raises: None
        """
        menu = QtWidgets.QMenu(parent=parent)
        return menu.menuAction()

    def create_action(self, parent):
        """Create and return a new action
        The parent of the action has to be set to ``parent``
        :param parent: The parent menu
        :type parent: :class:`PySide.QtGui.QMenu`
        :returns: The created action
        :rtype: :class:`PySide.QtGui.QAction`
        :raises: None
        """
        return QtWidgets.QAction(parent)

    def insert_menus(self, parent, first, last):
        """Create menus for rows first til last under the given parent
        :param parent: The parent index
        :type parent: :class:`PySide.QtCore.QModelIndex`
        :param first: the first row
        :type first: :class:`int`
        :param last: the last row
        :type last: :class:`int`
        :returns: None
        :rtype: None
        :raises: None
        """
        for i in range(first, last + 1):
            index = self._model.index(i, 0, parent)
            flattened = [index]
            flattened.extend(self._flatten_hierarchy(self._model, index))
            for newi in flattened:
                self.create_menu_for_index(newi)

    def remove_menus(self, parent, first, last):
        """Remove the menus under the given parent
        :param parent: the parent of the menus
        :type parent: :class:`PySide.QtCore.QModelIndex`
        :param first: the first row
        :type first: :class:`int`
        :param last: the last row
        :type last: :class:`int`
        :returns: None
        :rtype: None
        :raises: None
        """
        parentaction = self.get_action(parent)
        parentmenu = parentaction.menu()
        for i in reversed(range(first, last + 1)):
            index = self._model.index(i, 0, parent)
            action = self.get_action(index)
            parentmenu.removeAction(action)
        # menu has no childs, only display the action
        if not parentmenu.actions() and parentmenu is not self:
            parentaction.setMenu(None)

    def update_menus(self, topLeft, bottomRight):
        """Update the menus from topleft index to bottomright index
        :param topLeft: The top left index to update
        :type topLeft: :class:`PySide.QtCore.QModelIndex`
        :param bottomRight: the bottom right index to update
        :type bottomRight: :class:`PySide.QtCore.QModelIndex`
        :returns: None
        :rtype: None
        :raises: None
        """
        columns = [
            self.text_column,
            self.icon_column,
            self.icontext_column,
            self.tooltip_column,
            self.checked_column,
            self.whatsthis_column,
            self.statustip_column,
        ]
        needupdate = any([(c >= topLeft.column() and c <= bottomRight.column()) for c in columns])
        if needupdate:
            for row in range(topLeft.row(), bottomRight.row() + 1):
                index = topLeft.sibling(row, 0)
                action = self.get_action(index)
                self.set_action_data(action, index)

    def get_index(self, action, column=0):
        """Return the index for the given action
        :param action: the action to query
        :type action: :class:`PySide.QtGui.QAction`
        :param column: The column of the index
        :type column: :class:`int`
        :returns: the index of the action
        :rtype: :class:`PySide.QtCore.QModelIndex`
        :rasies: None
        """
        if action == self.menuAction():
            return QtCore.QModelIndex()
        # find all parents to get their index
        parents = self._get_parents(action)
        index = QtCore.QModelIndex()
        # Move through indexes down the chain
        for a in reversed(parents):
            parent = a.parent()
            # if parent of action is its own menu, get parent of that menu.
            # We want to know which row the action is in. For that we need
            # The real parent menu.
            if parent is a.menu():
                parent = parent.parent()
            row = parent.actions().index(a)
            index = self._model.index(row, 0, index)
        parent = action.parent()
        if parent is None:
            return index
        if parent is action.menu():
            parent = parent.parent()
        row = parent.actions().index(action)
        index = self._model.index(row, column, index)
        return index

    def _get_parents(self, action):
        parents = []
        a = action
        while True:
            parent = a.parent()
            # if the parent is the actions menu, we have to get
            # the menues parent. Else we get stuck on the same level.
            if parent and parent is a.menu():
                parent = parent.parent()
            if not isinstance(parent, QtWidgets.QMenu):
                # Is not part of the tree. Parent is not a menu but
                # might be None or another Widget
                return []
            # break if parent is root because we got all parents we need
            if parent is self:
                break
            # a new parent was found and we are still not at root
            # search further until we get to root
            parent = parent.menuAction()
            a = parent
            parents.append(parent)
        return parents

    def get_action(self, index):
        """Return the action for the given index
        :param index: the index to query
        :type index: :class:`PySide.QtCore.QModelIndex`
        :returns: the action for the given index
        :rtype: :class:`PySide.QtGui.QAction`
        :raises: None
        """
        if not index.isValid():
            return self.menuAction()
        parents = self._get_parent_indizes(index)
        menu = self
        for i in reversed(parents):
            action = menu.actions()[i.row()]
            menu = action.menu()
        try:
            return menu.actions()[index.row()]
        except IndexError:
            return None

    def _get_parent_indizes(self, index):
        if not index.isValid() or index.model() != self._model:
            return []
        parents = []
        i = index
        while True:
            p = i.parent()
            if not p.isValid():
                break
            parents.append(p)
            i = p
        return parents

    def set_action_data(self, action, index):
        """Set the data of the action for the given index
        .. Note:: The column of the index does not matter. The columns for the data
                  are specified in :data:`MenuView.setdataargs`.
        The arguments to used are defined in :data:`MenuView.setdataargs`.
        :param action: The action to update
        :type action: :class:`PySide.QtGui.QAction`
        :param index: The index with the data
        :type index: :class:`PySide.QtCore.QModelIndex`
        :returns: None
        :rtype: None
        :raises: None
        """
        self._set_action_enabled(action, index)
        self._set_action_checkable(action, index)
        for args in self.setdataargs:
            self._set_action_attribute(action, index, args)

    def _set_action_enabled(self, action, index):
        """Enable the action , depending on the item flags
        :param action: The action to update
        :type action: :class:`PySide.QtGui.QAction`
        :param index: the model index with the item flags
        :type index: :class:`PySide.QtCore.QModelIndex`
        :returns: None
        :rtype: None
        :raises: None
        """
        action.setEnabled(index.flags() & QtCore.Qt.ItemIsEnabled)

    def _set_action_checkable(self, action, index):
        """Set the action checkable, depending on the item flags
        .. Note:: The column of the index does not matter. The column for the data
                  is specified in :data:`MenuView.checked_column`.
        :param action: The action to update
        :type action: :class:`PySide.QtGui.QAction`
        :param index: the model index with the item flags
        :type index: :class:`PySide.QtCore.QModelIndex`
        :returns: None
        :rtype: None
        :raises: None
        """
        checkedindex = index.sibling(index.row(), self.checked_column)
        checkedflags = checkedindex.flags()
        action.setCheckable(checkedflags & QtCore.Qt.ItemIsUserCheckable)

    def _set_action_attribute(self, action, index, setdataarg):
        """Query the data of index and use it to set an attribute on action.
        .. Note:: The column of the index does not matter. The column for the data
                  is specified in ``setdataarg.column``.
        The data will be converted with ``setdataarg.convertfunc``.
        :param action: the action to update
        :type action: :class:`PySide.QtGui.QAction`
        :param index: the index with the data
        :type index: :class:`PySide.QtCore.QModelIndex`
        :param setdataarg: The container with arguments that define the way the data is applied
        :type setdataarg: :class:`SetDataArgs`
        :returns: None
        :rtype: None
        :raises: None
        """
        if isinstance(setdataarg.column, int):
            column = setdataarg.column
        else:
            column = getattr(self, setdataarg.column)
        data = self.get_data(index, setdataarg.role, column)
        if data is None:
            return
        setattrmethod = getattr(action, setdataarg.setfunc)
        if setdataarg.convertfunc:
            data = setdataarg.convertfunc(data)
        setattrmethod(data)

    @staticmethod
    def get_data(index, role, column=None):
        """Get data of the given index
        If the column is is not None and different from
        the index column, will get the data from a sibling
        index with the same row.
        :param index: The index to query for data
        :type index: :class:`PySide.QtCore.QModelIndex`
        :param role: the data role
        :type role: :data:`PySide.QtCore.Qt.ItemDataRole`
        :param column: the column of the row to query for data.
        :type column: :class:`int` | None
        :returns: The data retrieved
        :raises: None
        """
        if column and index.column() != column:
            index = index.sibling(index.row(), column)
        if index.isValid():
            return index.data(role)

    def _action_hovered(self, action):
        """Emit the hovered signal
        :param action: The action which emitted a hovered signal
        :type action: :class:`PySide.QtGui.QAction`
        :returns: None
        :rtype: None
        :raises: None
        """
        self._emit_signal_for_action(self.action_hovered, action)

    def _action_triggered(self, action, checked=False):
        """Emit the triggered signal
        :param action: The action which emitted a triggered signal
        :type action: :class:`PySide.QtGui.QAction`
        :param checked: True if the action was in a checked state
        :type checked: :class:`bool`
        :returns: None
        :rtype: None
        :raises: None
        """
        self._emit_signal_for_action(self.action_triggered, action, checked)

    def _action_toggled(self, action, checked=False):
        """Emit the toggled signal
        :param action: The action which emitted a toggled signal
        :type action: :class:`PySide.QtGui.QAction`
        :param checked: True if the action was in a checked state
        :type checked: :class:`bool`
        :returns: None
        :rtype: None
        :raises: None
        """
        self._emit_signal_for_action(self.action_toggled, action, checked)

    def _emit_signal_for_action(self, signal, action, *args):
        """Emit the given signal for the index of the given action
        :param signal: The signal to emit
        :type signal: :class:`PySide.QtCore.Signal`
        :param action: The action for which to emit the signal
        :type action: :class:`PySide.QtGui.QAction`
        :returns: None
        :rtype: None
        :raises: None
        """
        index = self.get_index(action)
        if index and index.isValid():
            signal.emit(index, *args)

    @staticmethod
    def _process_icondata(icondata):
        """Return an icon for the data of the :data:`PySide.QtCore.Qt.DecorationRole`
        :param icondata: The data from the :data:`PySide.QtCore.Qt.DecorationRole`
        :type icondata: :class:`PySide.QtGui.QIcon` | :class:`PySide.QtGui.QPixmap`
        :returns: A Icon based on the data.
        :rtype: :class:`PySide.QtGui.QIcon`
        :raises: None
        """
        if isinstance(icondata, QtGui.QIcon):
            return icondata
        if isinstance(icondata, QtGui.QPixmap):
            return QtGui.QIcon(icondata)

    @staticmethod
    def _checkconvertfunc(data):
        checkedstate = int(data) if data is not None else 0
        return checkedstate != QtCore.Qt.Unchecked


class SetDataArgs(object):
    """A container of arguments for setting attributes on an action.
    The data is queried from the model with ``role``. Then converted with ``convertfunc``.
    Then ``setfunc`` is used for setting the attribute on the action.
    ``convertfunc`` can be ``None``.
    If column is a string, the attribute of the view with that name will be used as column.
    """

    def __init__(self, setfunc, column, role, convertfunc):
        """Initialize a new container
        :raises: None
        """
        super(SetDataArgs, self).__init__()
        self.setfunc = setfunc
        self.column = column
        self.role = role
        self.convertfunc = convertfunc
