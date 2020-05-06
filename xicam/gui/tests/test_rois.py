from pytestqt import qtbot
from xicam.gui.widgets.ROI import ArcROI


def test_arcroi(qtbot):
    import pyqtgraph as pg
    import numpy as np

    imageview = pg.ImageView()
    data = np.random.random((10, 10))
    imageview.setImage(data)

    roi = ArcROI(center=(5, 5), radius=5)
    imageview.view.addItem(roi)
    imageview.show()

    # qtbot.addWidget(imageview)

    assert np.sum(roi.getArrayRegion(np.ones((10, 10)))) == 16

    qtbot.waitForWindowShown(imageview)
