from pyqtgraph import ImageView
import numpy as np


class DynImageView(ImageView):
    def __init__(self, *args, **kwargs):
        super(DynImageView, self).__init__(*args, **kwargs)

        # Use Viridis by default
        self.setPredefinedGradient('viridis')

        # Shrink LUT
        self.getHistogramWidget().setMinimumWidth(10)

        # Don't invert Y axis
        self.view.invertY(False)
        self.imageItem.setOpts(axisOrder='row-major')


        # Setup late signal
        self.sigTimeChangeFinished = self.timeLine.sigPositionChangeFinished

    def quickMinMax(self, data):
        """
        Estimate the min/max values of *data* by subsampling. MODIFIED TO USE THE 99TH PERCENTILE instead of max.
        """
        if data.size > 1e6:
            data = data[len(data) // 2]
        return np.nanmin(data), np.nanpercentile(data, 99)

    def setImage(self, img, **kwargs):
        super(DynImageView, self).setImage(img, **kwargs)
        if len(img.shape) > 2 and img.shape[0] == 1:
            self.ui.roiPlot.hide()

