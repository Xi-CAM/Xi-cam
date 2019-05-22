import collections
import logging

from event_model import DocumentRouter, RunRouter
import numpy
from matplotlib.backends.backend_qt5agg import (
    FigureCanvasQTAgg as FigureCanvas,
    NavigationToolbar2QT as NavigationToolbar)
from matplotlib.figure import Figure
import matplotlib
matplotlib.use('Qt5Agg')
import matplotlib.pyplot as plt  # noqa
from qtpy.QtWidgets import (  # noqa
    QLabel,
    QWidget,
    QVBoxLayout,
    )

from .hints import hinted_fields, guess_dimensions  # noqa


log = logging.getLogger('bluesky_browser')


class FigureManager:
    """
    For a given Viewer, encasulate the matplotlib Figures and associated tabs.
    """
    def __init__(self, add_tab):
        self.add_tab = add_tab
        self._figures = {}
        # Configuartion
        self.enabled = True
        self.exclude_streams = set()

    def get_figure(self, key, label, *args, **kwargs):
        try:
            return self._figures[key]
        except KeyError:
            return self._add_figure(key, label, *args, **kwargs)

    def _add_figure(self, key, label, *args, **kwargs):
        tab = QWidget()
        fig, _ = plt.subplots(*args, **kwargs)
        canvas = FigureCanvas(fig)
        canvas.setMinimumWidth(640)
        canvas.setParent(tab)
        toolbar = NavigationToolbar(canvas, tab)
        tab_label = QLabel(label)
        tab_label.setMaximumHeight(20)

        layout = QVBoxLayout()
        layout.addWidget(tab_label)
        layout.addWidget(canvas)
        layout.addWidget(toolbar)
        tab.setLayout(layout)
        self.add_tab(tab, label)
        self._figures[key] = fig
        return fig

    def __call__(self, name, start_doc):
        if not self.enabled:
            return [], []
        dimensions = start_doc.get('hints', {}).get('dimensions', guess_dimensions(start_doc))
        log.debug('dimensions: %s', dimensions)
        line_plot_manager = LinePlotManager(self, dimensions)
        rr = RunRouter([line_plot_manager])
        rr('start', start_doc)
        return [rr], []


class LinePlotManager:
    """
    Manage the line plots for one FigureManager.
    """
    def __init__(self, fig_manager, dimensions):
        self.fig_manager = fig_manager
        self.start_doc = None
        self.dimensions = dimensions
        self.dim_streams = set(stream for _, stream in self.dimensions)
        if len(self.dim_streams) > 1:
            raise NotImplementedError
        # Configuration
        self.omit_single_point_plot = True

    def __call__(self, name, start_doc):
        self.start_doc = start_doc
        return [], [self.subfactory]

    def subfactory(self, name, descriptor_doc):
        if self.omit_single_point_plot and self.start_doc.get('num_points') == 1:
            return []
        if len(self.dimensions) > 1:
            return []  # This is a job for Grid.
        fields = set(hinted_fields(descriptor_doc))
        # Filter out the fields with a data type or shape that we cannot
        # represent in a line plot.
        for field in list(fields):
            dtype = descriptor_doc['data_keys'][field]['dtype']
            if dtype not in ('number', 'integer'):
                fields.discard(field)
            ndim = len(descriptor_doc['data_keys'][field]['shape'] or [])
            if ndim != 0:
                fields.discard(field)

        callbacks = []
        dim_stream, = self.dim_streams  # TODO Handle multiple dim_streams.
        if descriptor_doc.get('name') == dim_stream:
            dimension, = self.dimensions
            x_keys, stream_name = dimension
            fields -= set(x_keys)
            assert stream_name == dim_stream  # TODO Handle multiple dim_streams.
            for x_key in x_keys:
                figure_label = f'Scalars v {x_key}'
                fig = self.fig_manager.get_figure(
                    (x_key, tuple(fields)), figure_label, len(fields), sharex=True)
                for y_key, ax in zip(fields, fig.axes):

                    log.debug('plot %s against %s', y_key, x_key)

                    ylabel = y_key
                    y_units = descriptor_doc['data_keys'][y_key].get('units')
                    ax.set_ylabel(y_key)
                    if y_units:
                        ylabel += f' [{y_units}]'
                    # Set xlabel only on lowest axes, outside for loop below.

                    def func(event_page, y_key=y_key):
                        """
                        Extract x points and y points to plot out of an EventPage.

                        This will be passed to LineWithPeaks.
                        """
                        y_data = event_page['data'][y_key]
                        if x_key == 'time':
                            t0 = self.start_doc['time']
                            x_data = numpy.asarray(event_page['time']) - t0
                        elif x_key == 'seq_num':
                            x_data = event_page['seq_num']
                        else:
                            x_data = event_page['data'][x_key]
                        return x_data, y_data

                    line = Line(func, ax=ax)
                    callbacks.append(line)

                if fields:
                    # Set the xlabel on the bottom-most axis.
                    if x_key == 'time':
                        xlabel = x_key
                        x_units = 's'
                    elif x_key == 'seq_num':
                        xlabel = 'sequence number'
                        x_units = None
                    else:
                        xlabel = x_key
                        x_units = descriptor_doc['data_keys'][x_key].get('units')
                    if x_units:
                        xlabel += f' [{x_units}]'
                    ax.set_xlabel(x_key)
                    fig.tight_layout()
            # TODO Plot other streams against time.
        for callback in callbacks:
            callback('start', self.start_doc)
            callback('descriptor', descriptor_doc)
        return callbacks


class Line(DocumentRouter):
    """
    Draw a matplotlib Line Arist update it for each Event.

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
    def __init__(self, func, *, label_template='{scan_id} [{uid:.8}]', ax=None, **kwargs):
        self.func = func
        if ax is None:
            import matplotlib.pyplot as plt
            _, ax = plt.subplots()
        self.ax = ax
        self.line, = ax.plot([], [], **kwargs)
        self.x_data = []
        self.y_data = []
        self.label_template = label_template
        self.label = kwargs.get('label')

    def start(self, doc):
        if self.label is None:
            d = collections.defaultdict(lambda: '?')
            d.update(**doc)
            label = self.label_template.format_map(d)
        else:
            label = self.label
        if label:
            self.line.set_label(label)
            self.ax.legend(loc='best')

    def event_page(self, doc):
        x, y = self.func(doc)
        self._update(x, y)

    def _update(self, x, y):
        """
        Takes in new x and y points and redraws plot if they are not empty.
        """
        if not len(x) == len(y):
            raise ValueError("User function is expected to provide the same "
                             "number of x and y points. Got {len(x)} x points "
                             "and {len(y)} y points.")
        if not x:
            # No new data. Short-circuit.
            return
        self.x_data.extend(x)
        self.y_data.extend(y)
        self.line.set_data(self.x_data, self.y_data)
        self.ax.relim(visible_only=True)
        self.ax.autoscale_view(tight=True)
        self.ax.figure.canvas.draw_idle()


class Grid(DocumentRouter):
    """
    Draw a matplotlib AxesImage Arist update it for each Event.

    The purposes of this callback is to create (on initialization) of a
    matplotlib grid image and then update it with new data for every `event`.
    NOTE: Some important parameters are fed in through **kwargs like `extent`
    which defines the axes min and max and `origin` which defines if the grid
    co-ordinates start in the bottom left or top left of the plot. For more
    info see https://matplotlib.org/tutorials/intermediate/imshow_extent.html
    or https://matplotlib.org/api/_as_gen/matplotlib.axes.Axes.imshow.html#matplotlib.axes.Axes.imshow

    Parameters
    ----------
    func : callable
        This must accept a BulkEvent and return three lists of floats (x
        grid co-ordinates, y grid co-ordinates and grid position intensity
        values). The three lists must contain an equal number of items, but
        that number is arbitrary. That is, a given document may add one new
        point, no new points or multiple new points to the plot.
    shape : tuple
        The (row, col) shape of the grid.
    ax : matplotlib Axes, optional.
        if ``None``, a new Figure and Axes are created.
    **kwargs
        Passed through to :meth:`Axes.imshow` to style the AxesImage object.
    """
    def __init__(self, func, shape, *, ax=None, **kwargs):
        self.func = func
        self.shape = shape
        if ax is None:
            _, ax = plt.subplots()
        self.ax = ax
        self.grid_data = numpy.full(self.shape, numpy.nan)
        self.image, = ax.imshow(self.grid_data, **kwargs)

    def event_page(self, doc):
        '''
        Takes in a bulk_events document and updates grid_data with the values
        returned from self.func(doc)

        Parameters
        ----------
        doc : dict
            The bulk event dictionary that contains the 'data' and 'timestamps'
            associated with the bulk event.

        Returns
        -------
        x_coords, y_coords, I_vals : Lists
            These are lists of x co-ordinate, y co-ordinate and intensity
            values arising from the bulk event.
        '''
        x_coords, y_coords, I_vals = self.func(doc)
        self._update(x_coords, y_coords, I_vals)

    def _update(self, x_coords, y_coords, I_vals):
        '''
        Updates self.grid_data with the values from the lists x_coords,
        y_coords, I_vals.

        Parameters
        ----------
        x_coords, y_coords, I_vals : Lists
            These are lists of x co-ordinate, y co-ordinate and intensity
            values arising from the event. The length of all three lists must
            be the same.
        '''

        if not len(x_coords) == len(y_coords) == len(I_vals):
            raise ValueError("User function is expected to provide the same "
                             "number of x, y and I points. Got {0} x points, "
                             "{1} y points and {2} I values."
                             "".format(len(x_coords), len(y_coords),
                                       len(I_vals)))

        if not x_coords:
            # No new data, Short-circuit.
            return

        # Update grid_data and the plot.
        self.grid_data[x_coords, y_coords] = I_vals
        self.image.set_array(self.grid_data)
