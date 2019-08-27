from xicam.plugins.dataresourceplugin import DataResourcePlugin
from urllib import parse


class SpotDataResourcePlugin(DataResourcePlugin):
    name = "Spot"

    def __init__(
        self, user="anonymous", password="", query="skipnum=0&sortterm=fs.stage_date&sorttype=desc&search=end_station=bl832"
    ):
        scheme = "https"
        host = "portal-auth.nersc.gov"
        path = "als/hdf/search"
        self.config = {"scheme": scheme, "host": host, "path": path, "query": query}
        super(SpotDataResourcePlugin, self).__init__(**self.config)
        from requests import Session

        self.session = Session()
        # self.session.post("https://newt.nersc.gov/newt/auth", {"username": user, "password": password})
        self._data = []
        # self.refresh()

    def columnCount(self, index=None):
        return len(self._data[0])

    def rowCount(self, index=None):
        return len(self._data)

    def data(self, index, role):
        from qtpy.QtCore import Qt, QVariant

        if index.isValid() and role == Qt.DisplayRole:
            return QVariant(self._data[index.row()]["name"])
        else:
            return QVariant()

            # TODO: remove qtcore dependence

    def refresh(self):
        oldrows = self.rowCount()
        uri = parse.ParseResult(
            scheme=self.config.get("scheme", ""),
            netloc=self.config.get("host", ""),
            path=self.config.get("path", ""),
            params=self.config.get("params", ""),
            query=self.config.get("query", ""),
            fragment=self.config.get("fragment", ""),
        )
        uri = parse.urlunparse(uri)
        r = self.session.get(uri)
        self._data = eval(r.content.replace(b"false", b"False"))
        # if hasattr(self.mod,'createIndex'):
        if self.model:
            self.dataChanged(self.model.createIndex(0, 0), self.model.createIndex(max(self.rowCount(), oldrows), 0))
            # if hasattr(self,'beginResetModel'):
            #     self.model.beginResetModel()
