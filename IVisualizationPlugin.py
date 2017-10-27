from qtpy.QtCore import *
from qtpy.QtWidgets import *
from yapsy.IPlugin import IPlugin


class _metaVisualizationPlugin(type(QWidget), type(IPlugin)):
    pass


class VisualizationPlugin(QWidget, IPlugin, metaclass=_metaVisualizationPlugin):
    pass


def test_VisualizationPlugin():
    from pyqtgraph import ImageView
    class ImageViewPlugin(VisualizationPlugin, ImageView):
        pass

    app = makeapp()
    i = ImageViewPlugin()
    i.show()
    t = QTimer()
    t.singleShot(1000, i.close)
    mainloop()


def makeapp():
    app = QApplication([])
    return app


def mainloop():
    app = QApplication.instance()
    app.exec_()
