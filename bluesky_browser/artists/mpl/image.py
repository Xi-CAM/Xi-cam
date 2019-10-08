import logging
from event_model import DocumentRouter
import numpy


log = logging.getLogger('bluesky_browser')


class Image(DocumentRouter):
    """
    Draw a matplotlib Image Arist update it for each Event.

    Parameters
    ----------
    func : callable
        This must accept an EventPage and return two lists of floats
        (x points and y points). The two lists must contain an equal number of
        items, but that number is arbitrary. That is, a given document may add
        one new point to the plot, no new points, or multiple new points.
    label_template : string
        This string will be formatted with the RunStart document. Any missing
        values will be filled with '?'. If the keyword argument 'label' is
        given, this argument will be ignored.
    ax : matplotlib Axes, optional
        If None, a new Figure and Axes are created.
    **kwargs
        Passed through to :meth:`Axes.plot` to style Line object.
    """
    def __init__(self, func, shape, *, label_template='{scan_id} [{uid:.8}]', ax=None, **kwargs):
        self.func = func
        if ax is None:
            import matplotlib.pyplot as plt
            _, ax = plt.subplots()
        self.ax = ax
        if len(self.ax.images) == 1:
            self.image, = self.ax.images
        elif len(self.ax.images) == 0:
            self.image = ax.imshow(numpy.zeros(shape), **kwargs)
            self.ax.figure.colorbar(self.image, ax=self.ax)
            self.label_template = label_template
        else:
            raise ValueError(f"Expected ax to be an axis with no image "
                             f"artists or one image artist. Found "
                             f"ax.images={self.ax.images}")

    def event_page(self, doc):
        data = self.func(doc)
        if data is not None:
            self._update(data)

    def _update(self, arr):
        """
        Takes in new array data and redraws plot if they are not empty.
        """
        if arr.ndim != 2:
            raise ValueError(
                f'The number of dimensions must be 2, but received array '
                f'has {arr.ndim} number of dimensions.')
        self.image.set_array(arr)
        new_clim = self.infer_clim(self.image.get_clim(), arr)
        self.image.set_clim(*new_clim)
        self.ax.figure.canvas.draw_idle()

    def infer_clim(self, current_clim, arr):
        return (min(current_clim[0], arr.min()), max(current_clim[1], arr.max()))
