from yapsy.IPlugin import IPlugin


class SettingsPlugin(IPlugin):
    def __init__(self, icon, name, widget):
        super(SettingsPlugin, self).__init__()
        self.icon = icon
        self.name = name
        self.widget = widget
        # self.setTextAlignment(Qt.AlignHCenter)
        # self.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
        # self.setSizeHint(QSize(136, 80))

    # def type(self):
    #     return self.UserType + 1