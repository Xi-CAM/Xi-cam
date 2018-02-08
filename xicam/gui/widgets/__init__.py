from xicam.plugins.GUIPlugin import GUILayout
from .motd import MOTD
from .dataresourcebrowser import DataResourceBrowser
from .previewwidget import PreviewWidget

from qtpy.QtWidgets import QApplication

if QApplication.instance():
    defaultstage = GUILayout(center=MOTD(),
                         left=DataResourceBrowser(),
                         lefttop=PreviewWidget())