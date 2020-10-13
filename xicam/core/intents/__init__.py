from typing import Union
import numpy as np
import xarray
import dask.array


class Intent:
    def __init__(self, item_name, canvas_name="", match_key=None, **kwargs):
        self._item_name = item_name
        self._canvas_name = canvas_name
        self.match_key = match_key
        self.kwargs = kwargs

    @property
    def item_name(self):
        return self._item_name

    @property
    def canvas_name(self):
        return self._canvas_name


class ImageIntent(Intent):
    # TODO: register as entrypoint
    canvas = "image_canvas"

    def __init__(self, image, *args, **kwargs):
        if "canvas_name" not in kwargs:
            kwargs["canvas_name"] = kwargs.get("item_name")
        super(ImageIntent, self).__init__(*args, **kwargs)
        self.image = image


class PlotIntent(Intent):
    # TODO: better labeling
    # canvas = {"qt": "plot_canvas"}
    canvas = "plot_canvas"

    def __init__(self, x: Union[np.ndarray, xarray.Dataset, dask.array.array],
                 y: Union[np.ndarray, xarray.Dataset, dask.array.array],
                 labels,
                 *args,
                 **kwargs):

        super(PlotIntent, self).__init__(*args, **kwargs)
        self.labels = labels
        self.x = x
        self.y = y
        self.match_key = kwargs.get("match_key", hash(frozenset(self.labels.items())))

    @property
    def canvas_name(self):
        if not self._canvas_name:
            x_name = self.labels.get("bottom", "")
            y_name = self.labels.get("left", "")
            return x_name + ", " + y_name
        return self._canvas_name
