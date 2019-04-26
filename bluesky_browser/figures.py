import logging

from event_model import DocumentRouter, RunRouter
import numpy
from matplotlib.backends.backend_qt5agg import (
    FigureCanvasQTAgg as FigureCanvas,
    NavigationToolbar2QT as NavigationToolbar)
from matplotlib.figure import Figure
import matplotlib
matplotlib.use('Qt5Agg')
import matplotlib.pyplot as plt
from qtpy.QtWidgets import (
    QLabel,
    QWidget,
    QVBoxLayout,
    )

from .hints import hinted_fields, guess_dimensions


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
            return
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
        fields = set(hinted_fields(descriptor_doc))

        callbacks = []
        dim_stream, = self.dim_streams  # TODO
        if descriptor_doc.get('name') == dim_stream:
            if self.omit_single_point_plot and self.start_doc.get('num_points') == 1:
                return []
            x_key, = self.dimensions[0][0]
            fields -= set([x_key])
            figure_label = f'Scalars v {x_key}'
            fig = self.fig_manager.get_figure(x_key, figure_label, len(fields), sharex=True)
            for y_key, ax in zip(fields, fig.axes):
                dtype = descriptor_doc['data_keys'][y_key]['dtype']
                if dtype not in ('number', 'integer'):
                    log.warn("Omitting %s from plot because dtype is %s",
                             y_key, dtype)
                    continue

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
    legend_keys : Iterable
        This collection of keys will be extracted from the RunStart document
        and shown in the legend with the corresponding values if present or
        'None' if not present. The default includes just one item, 'scan_id'.
        If a 'label' keyword argument is given, this paramter will be ignored
        and that label will be used instead.
    ax : matplotlib Axes, optional
        If None, a new Figure and Axes are created.
    **kwargs
        Passed through to :meth:`Axes.plot` to style Line object.
    """
    def __init__(self, func, *, legend_keys=('scan_id',), ax=None, **kwargs):
        self.func = func
        if ax is None:
            import matplotlib.pyplot as plt
            _, ax = plt.subplots()
        self.ax = ax
        self.line, = ax.plot([], [], **kwargs)
        self.x_data = []
        self.y_data = []
        self.legend_keys = legend_keys
        self.label = kwargs.get('label')

    def start(self, doc):
        if self.label is None:
            label = ' :: '.join([f'{key!s} {doc.get(key)!r}'
                                 for key in self.legend_keys])
            self.line.set_label(label)

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
