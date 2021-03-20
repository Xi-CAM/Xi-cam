from typing import Union, Dict, Iterable
import numpy as np
import xarray
import dask.array


# TODO: distinction between item_name and canvas_name and match_key?
# item_name: (display?) name of intent
# canvas_name:

class Intent:
    def __init__(self, name: str, canvas_name: str = None, match_key=None):
        self._name = name
        self.match_key = match_key
        self._canvas_name = canvas_name

    @property
    def name(self):
        return self._name

    @property
    def canvas_name(self):
        return self._canvas_name


class ImageIntent(Intent):
    canvas = "image_canvas"

    def __init__(self, name: str, image: np.ndarray, mixins: Iterable[str] = None, canvas_name: str = None,
                 match_key=None, **kwargs):
        super(ImageIntent, self).__init__(name, canvas_name, match_key)
        self.image = image
        self.mixins = mixins
        self.kwargs = kwargs

    @property
    def canvas_name(self):
        return self._canvas_name or self.name


class PlotIntent(Intent):
    canvas = "plot_canvas"

    def __init__(self,
                 name: str,
                 x: Union[np.ndarray, xarray.Dataset, dask.array.array],
                 y: Union[np.ndarray, xarray.Dataset, dask.array.array],
                 labels: Dict[str, str],
                 mixins: Iterable[str] = None,
                 canvas_name: str = None,
                 match_key=None,
                 **kwargs):
        super(PlotIntent, self).__init__(name, canvas_name, match_key)
        self.labels = labels
        self.x = x
        self.y = y
        self.mixins = mixins
        self.match_key = match_key or hash(frozenset(self.labels.items()))
        self.kwargs = kwargs

    @property
    def canvas_name(self):
        if not self._canvas_name:
            x_name = self.labels.get("bottom", "")
            y_name = self.labels.get("left", "")
            return x_name + ", " + y_name
        return self._canvas_name


class ScatterIntent(PlotIntent):
    """
    For reference on kwargs, see
    https://pyqtgraph.readthedocs.io/en/latest/graphicsItems/scatterplotitem.html
    """


class ErrorBarIntent(PlotIntent):
    """
    For reference on kwargs, see
    https://pyqtgraph.readthedocs.io/en/latest/graphicsItems/errorbaritem.html
    """


class BarIntent(Intent):
    canvas = "plot_canvas"

    def __init__(self,
                 name: str,
                 x: Union[np.ndarray, xarray.Dataset, dask.array.array],
                 labels: Dict[str, str],
                 canvas_name: str = None,
                 match_key=None,
                 **kwargs):

        if match_key is None:
            match_key = hash(frozenset(self.labels.items()))

        super(BarIntent, self).__init__(name, canvas_name, match_key)

        self.labels = labels
        self.x = x
        self.kwargs = kwargs

    @property
    def canvas_name(self):
        if not self._canvas_name:
            x_name = self.labels.get("bottom", "")
            y_name = self.labels.get("left", "")
            return x_name + ", " + y_name
        return self._canvas_name


class PairPlotIntent(Intent):
    canvas = 'pairplot_canvas'

    def __init__(self,
                 name: str,
                 transform_data: Union[np.ndarray, xarray.Dataset, dask.array.array],
                 canvas_name: str = None,
                 match_key=None,
                 **kwargs):
        if "canvas_name" not in kwargs:
            kwargs["canvas_name"] = kwargs.get("item_name")
        super(PairPlotIntent, self).__init__(name, canvas_name, match_key)
        self.transform_data = transform_data


class ROIIntent(Intent):
    canvas = "image_canvas"

    def __init__(self, name: str, roi: "pyqtgraph.ROI", canvas_name: str = None, match_key=None, **kwargs):
        super(ROIIntent, self).__init__(name, canvas_name, match_key)

        self.roi = roi

