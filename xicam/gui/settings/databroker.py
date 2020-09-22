from pathlib import Path

from databroker import catalog_search_path
from qtpy.QtCore import Signal, Qt, QItemSelection
from qtpy.QtGui import QIcon, QStandardItem, QStandardItemModel
from qtpy.QtWidgets import QAbstractItemView, QHBoxLayout, QLabel, QLineEdit, QTreeView, QVBoxLayout, QWidget

from xicam.plugins.settingsplugin import SettingsPlugin
from xicam.gui import static

EXTENSIONS = [".yaml", ".yml"]


class DatabrokerConfigModel(QStandardItemModel):
    config_file_role = Qt.UserRole + 1

    def __init__(self, *args, **kwargs):
        super(DatabrokerConfigModel, self).__init__(*args, **kwargs)
        self.setHorizontalHeaderLabels(["Databroker Configuration Files"])

    def add_config_dirs(self, config_dirs):
        for config_dir in config_dirs:
            self.add_config_dir(config_dir)

    def add_config_dir(self, config_dir):
        # Expecting a configuration directory that may contain databroker configuration files
        config_path = Path(config_dir)
        config_files = []
        if config_path.exists():
            config_path_item = QStandardItem()
            config_path_item.setData(str(config_path), Qt.DisplayRole)
            self.appendRow(config_path_item)
            config_files.extend([str(f) for f in config_path.iterdir() if f.suffix in EXTENSIONS])

            for config_file in config_files:
                config_file_item = QStandardItem()
                config_file_item.setData(str(config_file), Qt.DisplayRole)
                config_file_item.setData(config_file, self.config_file_role)
                config_path_item.appendRow(config_file_item)


class DatabrokerConfigView(QTreeView):
    sigConfigurationChanged = Signal(str)

    def __init__(self, parent=None):
        super(DatabrokerConfigView, self).__init__(parent)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        # self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)

    def selectionChanged(self, selected: QItemSelection, deselected: QItemSelection):
        selected_indexes = selected.indexes()
        if not selected_indexes:
            return
        data = selected_indexes[0].data(DatabrokerConfigModel.config_file_role)
        if data:
            print(data)
            self.sigConfigurationChanged.emit(data)

        super(DatabrokerConfigView, self).selectionChanged(selected, deselected)


class DatabrokerSettingsPlugin(SettingsPlugin):
    def __init__(self):

        self.activate_configuration = None

        # Grab all the databroker config (YAML) files
        self._model = DatabrokerConfigModel()
        self._model.add_config_dirs(catalog_search_path())

        # self._selectionModel = QItemSelectionModel(self._model)

        self._view = DatabrokerConfigView()
        self._view.setModel(self._model)
        # self._view.setSelectionModel(self._selectionModel)
        self._view.expandAll()

        self._current_configuration = QLineEdit("(None)")
        self._current_configuration.setReadOnly(True)

        def update_current_configuration_text(config_text):
            self._current_configuration.setText(config_text)

        self._view.sigConfigurationChanged.connect(update_current_configuration_text)

        layout = QVBoxLayout()
        layout.addWidget(self._view)

        inner_layout = QHBoxLayout()
        label = QLabel("Selected Databroker:")
        inner_layout.addWidget(label)
        inner_layout.addWidget(self._current_configuration)

        layout.addLayout(inner_layout)

        self._widget = QWidget()
        self._widget.setLayout(layout)

        name = "Databroker Configuration Files"
        icon = QIcon(static.path("icons/z.png"))
        super(DatabrokerSettingsPlugin, self).__init__(icon, name, self._widget)
        self.restore()

    @property
    def current_configuration(self) -> str:
        return self._current_configuration.text()
