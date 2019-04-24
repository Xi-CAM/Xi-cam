from event_model import DocumentRouter, RunRouter
from matplotlib.backends.backend_qt5agg import (
    FigureCanvasQTAgg as FigureCanvas,
    NavigationToolbar2QT as NavigationToolbar)
from matplotlib.figure import Figure
from qtpy.QtWidgets import (
    QLabel,
    QWidget,
    QVBoxLayout,
    )


class FigureManager:
    def __init__(self, add_tab):
        self.add_tab = add_tab
        self._figures = {}

    def get_figure(self, name):
        try:
            return self._figures[name]
        except KeyError:
            return self._add_figure(name)

    def _add_figure(self, name):
        tab = QWidget()
        fig = Figure((5.0, 4.0), dpi=100)
        canvas = FigureCanvas(fig)
        canvas.setMinimumWidth(640)
        canvas.setParent(tab)
        toolbar = NavigationToolbar(canvas, tab)
        tab_label = QLabel(name)
        # tab_label.setMaximumHeight(20)

        layout = QVBoxLayout()
        layout.addWidget(tab_label)
        layout.addWidget(canvas)
        layout.addWidget(toolbar)
        tab.setLayout(layout)
        self.add_tab(tab, name)
        self._figures[name] = fig
        return fig

    def __call__(self, name, start_doc):
        line_plot_manager = LinePlotManager(self)
        line_plot_manager('start', start_doc)
        return [RunRouter([line_plot_manager])], []


class LinePlotManager:
    def __init__(self, fig_manager):
        self.fig_manager = fig_manager

    def __call__(self, name, start_doc):
        line_plot_manager = LinePlotManager(self)
        fig = self.fig_manager.get_figure('test')
        fig.gca().plot([1,2,3])


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
