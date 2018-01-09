from xicam.plugins.GUIPlugin import GUILayout
from .splashwidget import SplashWidget
from .dataresourcebrowser import DataResourceBrowser
from .previewwidget import PreviewWidget

defaultstage = GUILayout(center=SplashWidget(),
                         left=DataResourceBrowser(),
                         lefttop=PreviewWidget())