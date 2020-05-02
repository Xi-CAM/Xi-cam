from pytestqt import qtbot


def test_IDataSourcePlugin(qtbot):
    from xicam.plugins.dataresourceplugin import DataResourcePlugin, DataSourceListModel

    class SpotDataResourcePlugin(DataResourcePlugin):
        def __init__(
            self,
            user="anonymous",
            password="",
            query="skipnum=0&sortterm=fs.stage_date&sorttype=desc&search=end_station=bl832",
        ):
            scheme = "https"
            host = "portal-auth.nersc.gov"
            path = "als/hdf/search"
            config = {"scheme": scheme, "host": host, "path": path, "query": query}
            super(SpotDataResourcePlugin, self).__init__(flags={"canPush": False}, **config)
            from requests import Session

            self.session = Session()
            self.refresh()
            try:
                self.session.post("https://newt.nersc.gov/newt/auth", {"username": user, "password": password})
            except ConnectionError:
                pass  # TODO: Something

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
            self._data = []
            try:
                r = self.session.get(
                    "https://portal-auth.nersc.gov/als/hdf/search?skipnum=0&limitnum=10&sortterm=fs.stage_date&sorttype=desc&search=end_station=bl832"
                )
                self._data = eval(r.content.replace(b"false", b"False"))
            except ConnectionError:
                pass  # TODO: SOMethING?

    # app = makeapp()
    # from qtpy.QtWidgets import QListView
    #
    # # TODO: handle password for testing
    # spot = DataSourceListModel(SpotDataResourcePlugin())
    #
    # lv = QListView()
    # lv.setModel(spot)
    # lv.show()
    # mainloop()

    spot = SpotDataResourcePlugin()
    assert spot.rowCount()
    qtbot.addWidget(spot)
