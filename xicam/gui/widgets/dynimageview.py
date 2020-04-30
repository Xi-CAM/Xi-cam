from pyqtgraph import ImageView
import numpy as np


class DynImageView(ImageView):
    def __init__(self, *args, **kwargs):
        super(DynImageView, self).__init__(*args, **kwargs)

        # Use Viridis by default
        self.setPredefinedGradient("viridis")

        # Shrink LUT
        self.getHistogramWidget().setMinimumWidth(10)

        # Don't invert Y axis
        self.view.invertY(False)
        self.imageItem.setOpts(axisOrder="row-major")

        # Setup late signal
        self.sigTimeChangeFinished = self.timeLine.sigPositionChangeFinished

    def quickMinMax(self, data):
        """
        Estimate the min/max values of *data* by subsampling. MODIFIED TO USE THE 99TH PERCENTILE instead of max.
        """
        if data is None:
            return 0, 0
        ax = np.argmax(data.shape)
        sl = [slice(None)] * data.ndim
        sl[ax] = slice(None, None, max(1, int(data.size // 1e6)))
        data = data[sl]
        return (
            np.nanpercentile(np.where(data > np.nanmin(data), data, np.nanmax(data)), 2),
            np.nanpercentile(np.where(data < np.nanmax(data), data, np.nanmin(data)), 98),
        )

    def setImage(self, img, **kwargs):
        super(DynImageView, self).setImage(img, **kwargs)
        if len(img.shape) > 2 and img.shape[0] == 1:
            self.ui.roiPlot.hide()
