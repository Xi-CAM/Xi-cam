import logging
import functools

from event_model import DocumentRouter
import numpy as np
from traitlets.config import Configurable
from traitlets.traitlets import Dict

from ..utils import load_config, Callable


log = logging.getLogger('bluesky_browser')


def first_frame(event_page, image_key):
    """
    Extract the first frame image data to plot out of an EventPage.
    """
    if event_page['seq_num'][0] == 1:
        data = np.asarray(event_page['data'][image_key])
        log.debug('Image from %s has shape %r', image_key, data.shape)
        if data.ndim == 3:
            # Axes are event axis, y, x. Slice out the first event.
            return data[0, ...]
        elif data.ndim == 4:
            # Axes are event axis, 'num_images' stack, y, x.
            # Slice out the first event and sum along 'num_images' stack.
            return data[0, ...].sum(0)
        else:
            raise ValueError(
                f'The number of dimensions for the image_key "{image_key}" '
                f'must be 3 or 4 for event page {event_page}, but received array '
                f'has {data.ndim} number of dimensions.')
    else:
        return None


def latest_frame(event_page, image_key):
    """
    Extract the most recent frame of image data to plot out of an EventPage.
    """
    data = np.asarray(event_page['data'][image_key])
    if event_page['seq_num'][0] == 1:
        # Just log once per event stream.
        log.debug('Image from %s has shape %r', image_key, data.shape)
    if data.ndim == 3:
        # Axes are event axis, y, x. Slice out the first event.
        return data[0, ...]
    elif data.ndim == 4:
        # Axes are event axis, 'num_images' stack, y, x.
        # Slice out the first event and sum along 'num_images' stack.
        return data[0, ...].sum(0)
    else:
        raise ValueError(
            f'The number of dimensions for the image_key "{image_key}" '
            f'must be 3 for event page {event_page}, but received array '
            f'has {data.ndim} number of dimensions.')


class BaseImageManager(Configurable):
    """
    Manage the image plots for one FigureManager.
    """
    imshow_options = Dict({}, config=True)

    def __init__(self, fig_manager, dimensions):
        self.update_config(load_config())
        self.fig_manager = fig_manager
        self.start_doc = None
        # We do not actually do anything with self.dimensions, just stashing it
        # here in case we need it later.
        self.dimensions = dimensions

    def __call__(self, name, start_doc):
        # We do not actually do anything with self.start_doc, just stashing it
        # here in case we need it later.
        self.start_doc = start_doc
        return [], [self.subfactory]

    def subfactory(self, name, descriptor_doc):
        image_keys = {}
        for key, data_key in descriptor_doc['data_keys'].items():
            ndim = len(data_key['shape'] or [])
            # We want to record a shape that will match the arr.shape
            # of the arrays we will see later. Ophyd has been writing
            # incorrect info into descriptors. We try to detect and correct
            # that here.
            if ndim == 2:
                image_keys[key] = data_key['shape']
            elif ndim == 3:
                # ophyd <1.4.0 gives (x, y, z) where z is 0
                # Maybe the better way to detect this is start['version']['ophyd'].
                if data_key['shape'][-1] == 0:
                    object_keys = descriptor_doc.get('object_keys', {})
                    for object_name, data_keys in object_keys.items():
                        if key in data_keys:
                            break
                    else:
                        log.debug("Couldn't find %s in object_keys %r", key, object_keys)
                        # Unable to handle this. Skip it.
                        continue
                    num_images = descriptor_doc['configuration'][object_name]['data'].get('num_images', -1)
                    x, y, _ = data_key['shape']
                    shape = (num_images, y, x)
                    image_keys[key] = shape[1:]  # Stash (y, x) shape alone.
                    log.debug("Patching the shape in the data key for %s"
                              "from %r to %r", key, data_key['shape'], shape)
                else:
                    # Assume we are getting correct metadata.
                    image_keys[key] = data_key['shape'][1:]  # Stash (y, x) shape alone.
            else:
                continue
            log.debug('%s has %d-dimensional image of shape %r',
                      key, ndim, shape)

        callbacks = []

        for image_key, shape in image_keys.items():
            caption_desc = f'{" ".join(self.func.__name__.split("_")).capitalize()}'
            figure_label = f'{caption_desc} of {image_key}'
            fig = self.fig_manager.get_figure(
                ('image', image_key), figure_label, 1)

            # If we are reusing an existing figure, it will have a second axis
            # for the colorbar, which we should ignore.
            # This is likely a bit brittle.
            ax, *_possible_colorbar = fig.axes

            log.debug('plot image %s', image_key)

            func = functools.partial(self.func, image_key=image_key)

            image = Image(func, shape=shape, ax=ax, **self.imshow_options)
            callbacks.append(image)

        for callback in callbacks:
            callback('start', self.start_doc)
            callback('descriptor', descriptor_doc)
        return callbacks


class FirstFrameImageManager(BaseImageManager):
    func = Callable(first_frame, config=True)


class LatestFrameImageManager(BaseImageManager):
    func = Callable(latest_frame, config=True)


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
            self.image = ax.imshow(np.zeros(shape), **kwargs)
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
