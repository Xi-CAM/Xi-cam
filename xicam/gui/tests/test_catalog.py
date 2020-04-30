from qtpy.QtWidgets import QLabel
from xicam.plugins import GUIPlugin, GUILayout
from xicam.gui.widgets.dynimageview import DynImageView
from xicam.gui.widgets.imageviewmixins import XArrayView
from xicam.core.data import MetaXArray


class TestPlugin(GUIPlugin):
    name = "catalogtest"

    def __init__(self):
        self.imageview = XArrayView()

        self.stages = {
            "Stage 1": GUILayout(self.imageview),
        }

        super(TestPlugin, self).__init__()

    def appendCatalog(self, runcatalog, **kwargs):
        xdata = runcatalog().primary.read()["random_img"][:, :, :, 0]  # The test data is 4-dimensional; ignoring last dim
        self.imageview.setImage(MetaXArray(xdata))

    def appendHeader(self):
        ...
