import logging
import functools

from event_model import DocumentRouter
from matplotlib.colors import LogNorm
import numpy as np
from traitlets.config import Configurable
from traitlets.traitlets import Dict

from ..utils import load_config, Callable


log = logging.getLogger('bluesky_browser')


def first_frame(event_page, image_key):
    """
    Extract image data to plot out of an EventPage.
    """
    if event_page['seq_num'][0] == 1:
        data = np.asarray(event_page['data'][image_key])
        if data.ndim != 3:
            raise ValueError(
                f'The number of dimensions for the image_key "{image_key}" '
                f'must be 3, but received array '
                f'has {data.ndim} number of dimensions.')
        return data[0, ...]
    else:
        return None


def latest_frame(event_page, image_key):
    """
    Extract image data to plot out of an EventPage.
    """
    data = np.asarray(event_page['data'][image_key])
    if data.ndim != 3:
        raise ValueError(
            f'The number of dimensions for the image_key "{image_key}" '
            f'must be 3, but received array '
            f'has {data.ndim} number of dimensions.')
    return data[0, ...]


class BaseImageManager(Configurable):
    """
    Manage the image plots for one FigureManager.
    """
    imshow_options = Dict({}, config=True)

    def __init__(self, fig_manager, dimensions):
        self.update_config(load_config())
        self.fig_manager = fig_manager
        self.start_doc = None
        self.dimensions = dimensions

    def __call__(self, name, start_doc):
        self.start_doc = start_doc
        return [], [self.subfactory]

    def subfactory(self, name, descriptor_doc):
        image_keys = {}
        for key, data_key in descriptor_doc['data_keys'].items():
            if len(data_key['shape'] or []) == 2:
                image_keys[key] = data_key['shape']

        callbacks = []

        for image_key, shape in image_keys.items():
            caption_desc = f'{" ".join(self.func.__name__.split("_")).capitalize()}'
            figure_label = f'{caption_desc} of {image_key}'
            fig = self.fig_manager.get_figure(
                ('image', image_key), figure_label, 1)

            ax, = fig.axes

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
        self.image = ax.imshow(np.zeros(shape), **kwargs)
        self.ax.figure.colorbar(self.image, ax=self.ax)
        self.label_template = label_template

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
        # self.ax.relim(visible_only=True)
        # self.ax.autoscale_view(tight=True)
        self.ax.figure.canvas.draw_idle()

    def infer_clim(self, current_clim, arr):
        return (min(current_clim[0], arr.min()), max(current_clim[1], arr.max()))


'''
def swviewer(hdr, SorW='s', panel='right', shift=True, name=''):
    """
    SWViewer is a SAXS or WAXS image viewer which takes either the SAXS or WAXS image and plots it
    a second image can be added later and the two will be shown side by side, (with joint zooming through scrolling)

    zooming in far enough will display pixel values for quanitative comparison

    eventually functionality for reduction to 1D plot which can be added to the frame will be added

    to add:
    share colorbar
    make colorbar better
    joint zooming, panning can be better
    panning is jerky
    zooming / panning is slow!

    :param hdr: header data for the image to plot
    :param SorW: 's' - saxs image  'w' - waxs image
    :param panel: 'left' or 'right'
    :param shift: True - shift the existing image in this panel to the other panel
    :return:
    """
    if SorW[0] is 's' or SorW[0] is 'S':
        data = next(hdr.data('Small and Wide Angle Synced CCD Detectors_saxs_image'))
    else:
        data = next(hdr.data('Small and Wide Angle Synced CCD Detectors_waxs_image'))
    fig = plt.figure('RSoXS Viewer')
    fig.set_tight_layout(1)
    if not fig.axes:
        #plot doesn't exist
        left_ax, right_ax = fig.subplots(1, 2)
        left_ax.set_title(name)
        right_ax.set_title(name)
        leftim = left_ax.imshow(data, norm=LogNorm())
        leftbar = plt.colorbar(leftim, ax=left_ax)
        rightim = right_ax.imshow(data, norm=LogNorm())
        rightbar = plt.colorbar(rightim, ax=right_ax)
        mngr = plt.get_current_fig_manager()
        mngr.window.setGeometry(0, 30, 1850, 1050)
        zpl = ZoomPan()
        #zpr = ZoomPan()
        scale = 1.5
        figZooml = zpl.zoom_factory(left_ax, base_scale=scale,joint=True)
        figZoomr = zpl.zoom_factory(right_ax, base_scale=scale,joint=True)
        figPanl = zpl.pan_factory(left_ax,joint=True)
        figPanr = zpl.pan_factory(right_ax,joint=True)
    else:
        left_ax, right_ax,l2,r2 = fig.axes
        if panel[0] is 'l' or panel[0] is 'L':
            if shift:
                right_ax.images[0].set_data(left_ax.images[0].get_array())
                right_ax.set_title(left_ax.get_title())
            left_ax.images[0].set_data(data)
            left_ax.set_title(name)
        else:
            if shift:
                left_ax.images[0].set_data(right_ax.images[0].get_array())
                left_ax.set_title(right_ax.get_title())
            right_ax.images[0].set_data(data)
            right_ax.set_title(name)
        left_ax.images[0].set_norm(LogNorm())
        right_ax.images[0].set_norm(LogNorm())
        leftbar = left_ax.images[0].colorbar
        rightbar = right_ax.images[0].colorbar
    num_ticks = 2
    leftbar.set_ticks(np.linspace(np.ceil(left_ax.images[0].get_array().max())+10, np.floor(left_ax.images[0].get_array().max()-10), num_ticks),update_ticks=True)
    leftbar.update_ticks()
    rightbar.set_ticks(np.linspace(np.ceil(right_ax.images[0].get_array().min())+10, np.floor(right_ax.images[0].get_array().max()-10), num_ticks),update_ticks=True)
    rightbar.update_ticks()

class ZoomPan:
    """
    stole this from an example on the web, added joint axes control as option (it was a bug that I fixed, now option!)

    """
    def __init__(self):
        self.press = None
        self.cur_xlim = None
        self.cur_ylim = None
        self.x0 = None
        self.y0 = None
        self.x1 = None
        self.y1 = None
        self.xpress = None
        self.ypress = None
        self.xzoom = True
        self.yzoom = True
        self.cidBP = None
        self.cidBR = None
        self.cidBM = None
        self.cidKeyP = None
        self.cidKeyR = None
        self.cidScroll = None
        self.plotted_text = [] # stores the pixel values that are plotted
        self.plotted_textjoint = []

    def zoom_factory(self, ax, base_scale = 2., joint=False):

        def zoom(event):
            if event.inaxes != ax and not joint : return
            cur_xlim = ax.get_xlim()
            cur_ylim = ax.get_ylim()

            xdata = event.xdata  # get event x location
            ydata = event.ydata  # get event y location
            if(xdata is None):
                return()
            if(ydata is None):
                return()

            if event.button == 'up':
                # deal with zoom in
                scale_factor = 1 / base_scale
            elif event.button == 'down':
                # deal with zoom out
                scale_factor = base_scale
            else:
                # deal with something that should never happen
                scale_factor = 1
                print(event.button)

            new_width = (cur_xlim[1] - cur_xlim[0]) * scale_factor
            new_height = (cur_ylim[1] - cur_ylim[0]) * scale_factor

            relx = (cur_xlim[1] - xdata)/(cur_xlim[1] - cur_xlim[0])
            rely = (cur_ylim[1] - ydata)/(cur_ylim[1] - cur_ylim[0])

            if(self.xzoom):
                ax.set_xlim([xdata - new_width * (1-relx), xdata + new_width * (relx)])
            if(self.yzoom):
                ax.set_ylim([ydata - new_height * (1-rely), ydata + new_height * (rely)])

            # Limits for the extent
            x_start = xdata - new_width * (1-relx)
            x_end = xdata + new_width * (relx)
            y_start = ydata - new_height * (1-rely)
            y_end = ydata + new_height * (rely)
            sizex = np.int(abs(x_end - x_start))
            sizey = np.int(abs(y_end - y_start))
            if event.inaxes != ax:
                for child in self.plotted_textjoint:
                    child.remove()
                    del(child)
                self.plotted_textjoint.clear()
                if sizex < 30 and sizey < 30:
                    # Add the text
                    jump_x = 0.5
                    jump_y = 0.5
                    x_positions = np.linspace(start=x_start + 1, stop=x_end + 1, num=sizex, endpoint=False)
                    y_positions = np.linspace(start=y_start, stop=y_end, num=sizey, endpoint=False)

                    for y_index, y in enumerate(y_positions):
                        for x_index, x in enumerate(x_positions):
                            label = ax.images[0].get_array()[np.int(y), np.int(x)]
                            text_x = x - jump_x
                            text_y = y - jump_y
                            self.plotted_textjoint.append(ax.text(text_x,
                                                             text_y,
                                                             label,
                                                             color='black',
                                                             ha='center',
                                                             va='center',
                                                             fontsize=10,
                                                             rotation=30))
            else:
                for child in self.plotted_text:
                    child.remove()
                    del (child)
                self.plotted_text.clear()
                if sizex < 30 and sizey < 30:
                    # Add the text
                    jump_x = 0.5
                    jump_y = 0.5
                    x_positions = np.linspace(start=x_start + 1, stop=x_end + 1, num=sizex, endpoint=False)
                    y_positions = np.linspace(start=y_start, stop=y_end, num=sizey, endpoint=False)

                    for y_index, y in enumerate(y_positions):
                        for x_index, x in enumerate(x_positions):
                            label = ax.images[0].get_array()[np.int(y), np.int(x)]
                            text_x = x - jump_x
                            text_y = y - jump_y
                            self.plotted_text.append(ax.text(text_x,
                                                             text_y,
                                                             label,
                                                             color='black',
                                                             ha='center',
                                                             va='center',
                                                             fontsize=10,
                                                             rotation=30))
            ax.figure.canvas.draw()
            ax.figure.canvas.flush_events()

        def onKeyPress(event):
            if event.key == 'x':
                self.xzoom = True
                self.yzoom = False
            if event.key == 'y':
                self.xzoom = False
                self.yzoom = True

        def onKeyRelease(event):
            self.xzoom = True
            self.yzoom = True

        fig = ax.get_figure() # get the figure of interest

        self.cidScroll = fig.canvas.mpl_connect('scroll_event', zoom)
        self.cidKeyP = fig.canvas.mpl_connect('key_press_event',onKeyPress)
        self.cidKeyR = fig.canvas.mpl_connect('key_release_event',onKeyRelease)

        return zoom

    def pan_factory(self, ax, joint = False):
        def onPress(event):
            if event.inaxes != ax and not joint: return
            self.cur_xlim = ax.get_xlim()
            self.cur_ylim = ax.get_ylim()
            self.press = self.x0, self.y0, event.xdata, event.ydata
            self.x0, self.y0, self.xpress, self.ypress = self.press


        def onRelease(event):
            self.press = None
            ax.figure.canvas.draw()

        def onMotion(event):
            if self.press is None: return
            if event.inaxes != ax and not joint: return
            dx = event.xdata - self.xpress
            dy = event.ydata - self.ypress
            self.cur_xlim -= dx
            self.cur_ylim -= dy
            ax.set_xlim(self.cur_xlim)
            ax.set_ylim(self.cur_ylim)



            sizex = np.int(abs(self.cur_xlim[1] - self.cur_xlim[0]))
            sizey = np.int(abs(self.cur_ylim[1] - self.cur_ylim[0]))
            if event.inaxes != ax:
                for child in self.plotted_textjoint:
                    child.remove()
                    del(child)
                self.plotted_textjoint.clear()
                if sizex < 30 and sizey < 30:
                    # Add the text
                    jump_x = 0.5
                    jump_y = 0.5
                    x_positions = np.linspace(start=self.cur_xlim[0]+1, stop=self.cur_xlim[1]+1, num=sizex, endpoint=False)
                    y_positions = np.linspace(start=self.cur_ylim[0], stop=self.cur_ylim[1], num=sizey, endpoint=False)

                    for y_index, y in enumerate(y_positions):
                        for x_index, x in enumerate(x_positions):
                            label = ax.images[0].get_array()[np.int(y), np.int(x)]
                            text_x = x - jump_x
                            text_y = y - jump_y
                            self.plotted_textjoint.append(ax.text(text_x,
                                                             text_y,
                                                             label,
                                                             color='black',
                                                             ha='center',
                                                             va='center',
                                                             fontsize=10,
                                                             rotation=30))
            else:
                for child in self.plotted_text:
                    child.remove()
                    del (child)
                self.plotted_text.clear()
                if sizex < 30 and sizey < 30:
                    # Add the text
                    jump_x = 0.5
                    jump_y = 0.5
                    x_positions = np.linspace(start=self.cur_xlim[0] + 1, stop=self.cur_xlim[1] + 1, num=sizex,
                                              endpoint=False)
                    y_positions = np.linspace(start=self.cur_ylim[0], stop=self.cur_ylim[1], num=sizey, endpoint=False)

                    for y_index, y in enumerate(y_positions):
                        for x_index, x in enumerate(x_positions):
                            label = ax.images[0].get_array()[np.int(y), np.int(x)]
                            text_x = x - jump_x
                            text_y = y - jump_y
                            self.plotted_text.append(ax.text(text_x,
                                                             text_y,
                                                             label,
                                                             color='black',
                                                             ha='center',
                                                             va='center',
                                                             fontsize=10,
                                                             rotation=30))
            ax.figure.canvas.draw()
            ax.figure.canvas.flush_events()


        fig = ax.get_figure() # get the figure of interest

        self.cidBP = fig.canvas.mpl_connect('button_press_event',onPress)
        self.cidBR = fig.canvas.mpl_connect('button_release_event',onRelease)
        self.cidBM = fig.canvas.mpl_connect('motion_notify_event',onMotion)
        # attach the call back

        #return the function
        return onMotion

def spawn_quick_view(name, doc):
    if name == 'stop':
        # A run just completed. Look it up in databroker.
        uid = doc['run_start']  # the 'Run Start UID' used to identify a run.
        hdr = db[uid]
        if 'Small and Wide' in hdr['start']['detectors'][0]:
            swviewer(hdr,'w','left',False,'WAXS')
            swviewer(hdr,'s','right',False,'SAXS')

#RE.subscribe(spawn_quick_view) # will change this to SW viewer, but eventually need to load during scan, not just after

"""
Interactive tool to draw mask on an image or image-like array.
Adapted from matplotlib/examples/event_handling/poly_editor.py

no working completely yet on plots with two images - need to split it out better
"""

import matplotlib.pyplot as plt
from matplotlib.patches import Polygon
from matplotlib.mlab import dist_point_to_segment



class MaskCreator(object):
    """An interactive polygon editor.
    Parameters
    ----------
    poly_xy : list of (float, float)
        List of (x, y) coordinates used as vertices of the polygon.
    max_ds : float
        Max pixel distance to count as a vertex hit.
    Key-bindings
    ------------
    't' : toggle vertex markers on and off.  When vertex markers are on,
          you can move them, delete them
    'd' : delete the vertex under point
    'i' : insert a vertex at point.  You must be within max_ds of the
          line connecting two existing vertices
    """
    def __init__(self, ax, poly_xy=None, max_ds=10):
        self.showverts = True
        self.max_ds = max_ds
        if poly_xy is None:
            poly_xy = default_vertices(ax)
        self.poly = Polygon(poly_xy, animated=True,
                            fc='y', ec='none', alpha=0.4)

        ax.add_patch(self.poly)
        ax.set_clip_on(False)
        ax.set_title("Click and drag a point to move it; "
                     "'i' to insert; 'd' to delete.\n"
                     "Close figure when done.")
        self.ax = ax

        x, y = zip(*self.poly.xy)
        self.line = plt.Line2D(x, y, color='none', marker='o', mfc='r',
                               alpha=0.2, animated=True)
        self._update_line()
        self.ax.add_line(self.line)

        self.poly.add_callback(self.poly_changed)
        self._ind = None # the active vert

        canvas = self.poly.figure.canvas
        canvas.mpl_connect('draw_event', self.draw_callback)
        canvas.mpl_connect('button_press_event', self.button_press_callback)
        canvas.mpl_connect('button_release_event', self.button_release_callback)
        canvas.mpl_connect('key_press_event', self.key_press_callback)
        canvas.mpl_connect('motion_notify_event', self.motion_notify_callback)
        self.canvas = canvas

    def get_mask(self, shape):
        """Return image mask given by mask creator"""
        h, w = shape
        y, x = np.mgrid[:h, :w]
        points = np.transpose((x.ravel(), y.ravel()))
        mask = self.verts.contains_points(points)
        return mask.reshape(h, w)

    def poly_changed(self, poly):
        'this method is called whenever the polygon object is called'
        # only copy the artist props to the line (except visibility)
        vis = self.line.get_visible()
        #Artist.update_from(self.line, poly)
        self.line.set_visible(vis)  # don't use the poly visibility state

    def draw_callback(self, event):
        self.background = self.canvas.copy_from_bbox(self.ax.bbox)
        self.ax.draw_artist(self.poly)

        self.ax.draw_artist(self.line)
        self.canvas.blit(self.ax.bbox)

    def button_press_callback(self, event):
        'whenever a mouse button is pressed'
        ignore = not self.showverts or event.inaxes is None or event.button != 1
        if ignore:
            return
        self._ind = self.get_ind_under_cursor(event)

    def button_release_callback(self, event):
        'whenever a mouse button is released'
        ignore = not self.showverts or event.button != 1
        if ignore:
            return
        self._ind = None

    def key_press_callback(self, event):
        'whenever a key is pressed'
        if not event.inaxes:
            return
        if event.key=='t':
            self.showverts = not self.showverts
            self.line.set_visible(self.showverts)
            if not self.showverts:
                self._ind = None
        elif event.key=='d':
            ind = self.get_ind_under_cursor(event)
            if ind is None:
                return
            if ind == 0 or ind == self.last_vert_ind:
                print("Cannot delete root node")
                return
            self.poly.xy = [tup for i,tup in enumerate(self.poly.xy)
                                if i!=ind]
            self._update_line()
        elif event.key=='i':
            xys = self.poly.get_transform().transform(self.poly.xy)
            p = event.x, event.y # cursor coords
            for i in range(len(xys)-1):
                s0 = xys[i]
                s1 = xys[i+1]
                d = dist_point_to_segment(p, s0, s1)
                if d <= self.max_ds:
                    self.poly.xy = np.array(
                        list(self.poly.xy[:i+1]) +
                        [(event.xdata, event.ydata)] +
                        list(self.poly.xy[i+1:]))
                    self._update_line()
                    break
        self.canvas.draw()

    def motion_notify_callback(self, event):
        'on mouse movement'
        ignore = (not self.showverts or event.inaxes is None or
                  event.button != 1 or self._ind is None)
        if ignore:
            return
        x,y = event.xdata, event.ydata

        if self._ind == 0 or self._ind == self.last_vert_ind:
            self.poly.xy[0] = x,y
            self.poly.xy[self.last_vert_ind] = x,y
        else:
            self.poly.xy[self._ind] = x,y
        self._update_line()

        self.canvas.restore_region(self.background)
        self.ax.draw_artist(self.poly)
        self.ax.draw_artist(self.line)
        self.canvas.blit(self.ax.bbox)

    def _update_line(self):
        # save verts because polygon gets deleted when figure is closed
        self.verts = self.poly.xy
        self.last_vert_ind = len(self.poly.xy) - 1
        self.line.set_data(zip(*self.poly.xy))

    def get_ind_under_cursor(self, event):
        'get the index of the vertex under cursor if within max_ds tolerance'
        # display coords
        xy = np.asarray(self.poly.xy)
        xyt = self.poly.get_transform().transform(xy)
        xt, yt = xyt[:, 0], xyt[:, 1]
        d = np.sqrt((xt - event.x)**2 + (yt - event.y)**2)
        indseq = np.nonzero(np.equal(d, np.amin(d)))[0]
        ind = indseq[0]
        if d[ind] >= self.max_ds:
            ind = None
        return ind


def default_vertices(ax):
    """Default to rectangle that has a quarter-width/height border."""
    xlims = ax.get_xlim()
    ylims = ax.get_ylim()
    w = np.diff(xlims)
    h = np.diff(ylims)
    x1, x2 = xlims + w // 4 * np.array([1, -1])
    y1, y2 = ylims + h // 4 * np.array([1, -1])
    return ((x1, y1), (x1, y2), (x2, y2), (x2, y1))

"""
add in some archiver plotting rouines, for vacuum, any old motor etc etc


"""
'''

pass
