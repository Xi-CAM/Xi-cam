import requests
from qtpy.QtCore import *
from qtpy.QtGui import *
from qtpy.QtWidgets import *
from xicam.gui.static import path
from xicam.gui.widgets.searchlineedit import SearchLineEdit
from copy import deepcopy

from xicam.plugins import SettingsPlugin, manager


class ConnectionSettingsPlugin(SettingsPlugin):
    """
    A built-in settings plugin to configure connections to other hosts
    """

    def __init__(self):
        # Setup UI
        self.widget = QWidget()
        self.widget.setLayout(QHBoxLayout())
        self.listview = QListView()
        self.connectionsmodel = QStandardItemModel()
        self.listview.setModel(self.connectionsmodel)

        self.plugintoolbar = QToolBar()
        self.plugintoolbar.setOrientation(Qt.Vertical)
        self.plugintoolbar.addAction(QIcon(str(path("icons/plus.png"))), "Add plugin", self.add_credential)
        self.plugintoolbar.addAction(QIcon(str(path("icons/minus.png"))), "Remove plugin", self.remove_credential)
        self.widget.layout().addWidget(self.listview)
        self.widget.layout().addWidget(self.plugintoolbar)
        super(ConnectionSettingsPlugin, self).__init__(QIcon(str(path("icons/server.png"))), "Connections", self.widget)

    def add_credential(self):
        """
        Open the CamMart install dialog
        """
        self._dialog = CredentialDialog()
        self._dialog.sigAddCredential.connect(self._add_credential)
        self._dialog.exec_()

    def remove_credential(self):
        """
        Removes a credential
        """
        if self.listview.selectedIndexes():
            self.connectionsmodel.removeRow(self.listview.selectedIndexes()[0].row())

    def _add_credential(self, name: str, credential: dict):
        item = QStandardItem(name)
        item.credential = credential
        item.name = name
        self.connectionsmodel.appendRow(item)
        self.connectionsmodel.dataChanged.emit(item.index(), item.index())

    def toState(self):
        credentials = deepcopy(self.credentials)
        for name, credential in credentials.items():
            if credential.get("savepassword", False):
                credential["password"] = None
        return credentials

    def fromState(self, state):
        self.connectionsmodel.clear()
        for name, credential in state.items():
            item = QStandardItem(name)
            item.credential = credential
            item.name = name
            self.connectionsmodel.appendRow(item)
        self.listview.reset()

    @property
    def credentials(self):
        return {
            self.connectionsmodel.item(i).name: self.connectionsmodel.item(i).credential
            for i in range(self.connectionsmodel.rowCount())
        }


class CredentialDialog(QDialog):
    sigAddCredential = Signal(str, dict)
    sigConnect = Signal(dict)

    def __init__(self, addmode=True):
        super(CredentialDialog, self).__init__()

        # Set size and position
        # self.setGeometry(0, 0, 800, 500)
        frameGm = self.frameGeometry()
        screen = QApplication.desktop().screenNumber(QApplication.desktop().cursor().pos())
        centerPoint = QApplication.desktop().screenGeometry(screen).center()
        frameGm.moveCenter(centerPoint)
        self.move(frameGm.topLeft())

        # Setup fields
        self.host = QLineEdit()
        self.profiles = QComboBox()
        self.profiles.addItem("New...")
        self.profilename = QLineEdit()
        self.username = QLineEdit()
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.Password)
        self.savepassword = QCheckBox("Save Password")
        self.rememberprofile = QCheckBox("Remember Profile")

        # Setup dialog buttons
        self.addButton = QPushButton("&Add")
        self.connectButton = QPushButton("C&onnect")
        self.cancelButton = QPushButton("&Cancel")
        self.addButton.clicked.connect(self.add)
        self.connectButton.clicked.connect(self.connect)
        self.cancelButton.clicked.connect(self.close)
        self.profiles.currentTextChanged.connect(self.loadProfile)
        self.buttonboxWidget = QDialogButtonBox()
        if addmode:
            self.buttonboxWidget.addButton(self.addButton, QDialogButtonBox.AcceptRole)
        else:
            self.buttonboxWidget.addButton(self.connectButton, QDialogButtonBox.AcceptRole)

        self.buttonboxWidget.addButton(self.cancelButton, QDialogButtonBox.RejectRole)

        # Compose main layout
        mainLayout = QFormLayout()
        if not addmode:
            mainLayout.addRow("Profile", self.profiles)
        mainLayout.addRow("Profile", self.profilename)
        mainLayout.addRow("Host", self.host)
        mainLayout.addRow("Username", self.username)
        mainLayout.addRow("Password", self.password)
        mainLayout.addRow(self.savepassword)
        if not addmode:
            mainLayout.addRow(self.rememberprofile)
        mainLayout.addRow(self.buttonboxWidget)

        # Populate profiles
        for name, credential in manager.get_plugin_by_name("Connections", "SettingsPlugin").credentials.items():
            self.profiles.addItem(name)

        self.setLayout(mainLayout)
        self.setWindowTitle("Add Connection...")

        # Set modality
        self.setModal(True)

    def loadProfile(self):
        profilename = self.profiles.currentText()
        if profilename == "New...":
            self.username.setEnabled(True)
            self.password.setEnabled(True)
            self.host.setEnabled(True)
            self.savepassword.setEnabled(True)
            self.rememberprofile.setVisible(True)
        else:
            credential = manager.get_plugin_by_name("Connections", "SettingsPlugin").credentials[profilename]
            self.username.setText(credential["username"])
            self.host.setText(credential["host"])
            self.password.setText(credential["password"])
            self.savepassword.setChecked(credential["savepassword"])
            self.profilename.setText(profilename)
            self.username.setEnabled(False)
            self.password.setEnabled(False)
            self.host.setEnabled(False)
            self.savepassword.setEnabled(False)
            self.rememberprofile.setVisible(False)

    def add(self):
        self.sigAddCredential.emit(
            self.profilename.text(),
            {
                "host": self.host.text(),
                "username": self.username.text(),
                "password": self.password.text(),
                "savepassword": False,
            },
        )
        self.accept()

    def connect(self):
        if self.rememberprofile.isChecked():
            self.add()
        self.sigConnect.emit(
            {
                "host": self.host.text(),
                "username": self.username.text(),
                "password": self.password.text(),
                "savepassword": False,
            }
        )
        self.accept()  # Segfault?


class ConnectDelegate(QItemDelegate):
    def __init__(self, parent):
        super(ConnectDelegate, self).__init__(parent)
        self._parent = parent

    def paint(self, painter, option, index):
        if not self._parent.indexWidget(index):
            button = QToolButton(self.parent())
            button.setAutoRaise(True)
            button.setText("Delete Operation")
            button.setIcon(QIcon(path("icons/trash.png")))
            sp = QSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)
            sp.setWidthForHeight(True)
            button.setSizePolicy(sp)
            button.clicked.connect(index.data())

            self._parent.setIndexWidget(index, button)
