from xicam.plugins.guiplugin import GUILayout
from .motd import MOTD
from .dataresourcebrowser import DataResourceBrowser
from .previewwidget import PreviewWidget

_defaultstage = None


def get_default_stage():
    global _defaultstage
    if not _defaultstage:
        _defaultstage = GUILayout(center=MOTD(), left=DataResourceBrowser(), lefttop=PreviewWidget())
    return _defaultstage
