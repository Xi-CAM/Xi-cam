from .plugin import PluginType

viewTypes = ["ListView", "TreeView", ""]

try:
    from qtpy.QtCore import *

    class DataSourceListModel(QAbstractListModel):
        def __init__(self, dataresource):
            super(DataSourceListModel, self).__init__()
            self.dataresource = dataresource
            self.dataresource.model = self
            self.rowCount = dataresource.rowCount
            self.data = dataresource.data
            self.columnCount = dataresource.columnCount
            self.refresh = dataresource.refresh

        @property
        def config(self):
            return self.dataresource.config

        @property
        def uri(self):
            return self.dataresource.uri

        @uri.setter
        def uri(self, value):
            self.dataresource.uri = value

        def __getattr__(self, attr):  ## implicitly wrap methods from leftViewer
            if hasattr(self.dataresource, attr):
                m = getattr(self.dataresource, attr)
                return m
            raise NameError(attr)


except ImportError:
    # TODO: how should this be handled?
    pass


class DataResourcePlugin(PluginType):
    from xicam.gui.widgets.dataresourcebrowser import DataResourceList, DataBrowser

    model = DataSourceListModel
    view = DataResourceList
    controller = DataBrowser

    is_singleton = False
    needs_qt = True

    name = ""

    def __init__(self, flags: dict = None, **config):
        """
        Config keys should follow RFC 3986 URI format:
            scheme:[//[user[:password]@]host[:port]][/path][?query][#fragment]

        Should provide the abstract methods required of QAbstractItemModel. While this plugin does not depend on Qt, it
        mimics the same functionality, and so can easily be wrapped in a QAbstractItemModel for GUI views. A parent
        model assigns itself to self.model
        """
        super(DataResourcePlugin, self).__init__()
        # self.model = None
        self.config = config
        self.flags = flags if flags else {"isFlat": True, "canPush": False}
        # self.uri=''

        import warnings

        warnings.warn("The DataResourcePlugin is being deprecated in favor of CatalogPlugin.", DeprecationWarning)

    def pushData(self, *args, **kwargs):
        raise NotImplementedError

    def dataChanged(self, topleft=None, bottomright=None):
        if self.model:
            self.model.dataChanged.emit(topleft, bottomright)

    def columnCount(self, index=None):
        raise NotImplementedError

    def rowCount(self, index=None):
        raise NotImplementedError

    def data(self, index, role):
        raise NotImplementedError

    def headerData(self, column, orientation, role):
        raise NotImplementedError

    def index(self, row, column, parent):
        raise NotImplementedError

    def parent(self, index):
        raise NotImplementedError

    @property
    def host(self):
        return self.config["host"]

    @property
    def path(self):
        return self.config["path"]

    def refresh(self):
        pass

    # TODO: convenience properties for each config
