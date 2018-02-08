from pyqtgraph import ImageView
import numpy as np


class DynImageView(ImageView):
    def __init__(self, *args, **kwargs):
        super(DynImageView, self).__init__(*args, **kwargs)

        # Use Viridis by default
        self.setPredefinedGradient('viridis')

        # Shrink LUT
        self.getHistogramWidget().setMinimumWidth(10)

    def quickMinMax(self, data):
        """
        Estimate the min/max values of *data* by subsampling. MODIFIED TO USE THE 99TH PERCENTILE instead of max.
        """
        if data.size > 1e6:
            data = data[len(data) // 2]
        return np.nanmin(data), np.nanpercentile(data, 99)
