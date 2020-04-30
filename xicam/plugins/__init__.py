import sys
import os
import platform
import itertools
import warnings

import entrypoints
from appdirs import user_config_dir, site_config_dir, user_cache_dir

from xicam.core import msg
from xicam.core import threads
from xicam.core.args import parse_args

from .datahandlerplugin import DataHandlerPlugin
from .catalogplugin import CatalogPlugin
from .guiplugin import GUIPlugin, GUILayout
from .operationplugin import OperationPlugin
from .settingsplugin import SettingsPlugin, ParameterSettingsPlugin
from .dataresourceplugin import DataResourcePlugin
from .controllerplugin import ControllerPlugin
from .widgetplugin import QWidgetPlugin
from .plugin import PluginType

try:
    # try to find the venvs entrypoint
    if "cammart" in entrypoints.get_group_named(f"xicam.plugins.SettingsPlugin") and not "--no-cammart" in sys.argv:
        from xicam.gui.cammart.venvs import observers as venvsobservers
        from xicam.gui.cammart import venvs
    else:
        raise ImportError
except ImportError:
    venvsobservers = None
from .dataresourceplugin import DataResourcePlugin
from .fittablemodelplugin import Fittable1DModelPlugin
from .ezplugin import _EZPlugin, EZPlugin
from .hints import PlotHint, Hint

from queue import LifoQueue
from enum import Enum, auto
from contextlib import contextmanager
from timeit import default_timer

import time

op_sys = platform.system()
if op_sys == "Darwin":  # User config dir incompatible with venv on darwin (space in path name conflicts)
    user_plugin_dir = os.path.join(user_cache_dir(appname="xicam"), "plugins")
else:
    user_plugin_dir = os.path.join(user_config_dir(appname="xicam"), "plugins")
site_plugin_dir = os.path.join(site_config_dir(appname="xicam"), "plugins")



@contextmanager
def load_timer():
    start = default_timer()
    elapser = lambda: default_timer() - start
    yield lambda: elapser()
    end = default_timer()
    elapser = lambda: end - start


class State(Enum):
    READY = auto()
    DISCOVERING = auto()
    LOADING = auto()
    INSTANTIATING = auto()


class Filters(Enum):
    UPDATE = auto()
    COMPLETE = auto()


class XicamPluginManager:
    def __init__(self, qt_is_safe=False):

        self.qt_is_safe = qt_is_safe
        self._blacklist = []
        self._load_queue = LifoQueue()
        self._instantiate_queue = LifoQueue()
        self._entrypoints = {}
        self._load_cache = {}
        self._observers = []
        self.state = State.READY
        self.type_mapping = {}
        self.plugin_types = {}

        # Remember all modules loaded before any plugins are loaded; don't bother unloading these
        self._preloaded_modules = set(sys.modules.keys())

        # Observe changes to venvs
        if venvsobservers is not None:
            venvsobservers.append(self)

        self.initialize_types()

        # Check if cammart should be ignored
        try:
            args = parse_args(exit_on_fail=False)
            include_cammart = not args.nocammart
            self._blacklist = args.blacklist
        except RuntimeError:
            include_cammart = False

        # ...if so, blacklist it
        if not include_cammart:
            self._blacklist.extend(["cammart", "venvs"])

    def initialize_types(self):
        # Load plugin types
        self.plugin_types = {name: ep.load() for name, ep in entrypoints.get_group_named("xicam.plugins.PluginType").items()}

        # Toss plugin types that need qt if running without qt
        if not self.qt_is_safe:
            self.plugin_types = {
                type_name: type_class
                for type_name, type_class in self.plugin_types.items()
                if not getattr(type_class, "needs_qt", True)
            }

        # Initialize types
        self.type_mapping = {type_name: {} for type_name in self.plugin_types.keys()}
        self._entrypoints = {type_name: {} for type_name in self.plugin_types.keys()}
        self._load_cache = {type_name: {} for type_name in self.plugin_types.keys()}

    def collect_plugins(self):
        """
        Find, load, and instantiate all Xi-cam plugins matching known plugin types

        """
        self._discover_plugins()
        self._load_plugins()

    def collect_plugin(self, plugin_name, plugin_class, type_name, replace=False):
        """
        Register a class as a plugin. For in-memory usage. If `replace`, then any earlier instances are purged first

        """
        if replace:
            # Clear cache by name
            self._entrypoints[type_name].pop(plugin_name, None)
            self.type_mapping[type_name].pop(plugin_name, None)
            self._load_cache[type_name].pop(plugin_name, None)
        else:
            try:
                assert plugin_name not in self.type_mapping[type_name]
            except AssertionError:
                raise ValueError(f"A plugin named {plugin_name} has already been loaded. Supply `replace=True` to override.")

        # Start a special collection cycle
        self.state = State.DISCOVERING
        live_entry_point = LiveEntryPoint(plugin_name, plugin_class)
        self._load_queue.put((type_name, live_entry_point))
        if self.state == State.DISCOVERING:
            self.state = State.LOADING
        self._load_plugins()

    def _unload_plugins(self):
        assert self.state == State.READY
        self._load_queue = LifoQueue()
        self._instantiate_queue = LifoQueue()

        # Initialize types
        self.type_mapping = {type_name: {} for type_name in self.plugin_types.keys()}
        self._entrypoints = {type_name: {} for type_name in self.plugin_types.keys()}
        self._load_cache = {type_name: {} for type_name in self.plugin_types.keys()}

        reload_candidates = list(filter(lambda key: key.startswith("xicam."), sys.modules.keys()))
        for module_name in reload_candidates:
            if module_name not in self._preloaded_modules:
                del sys.modules[module_name]

    def hot_reload(self):
        warnings.warn("Hot-reloading plugins; unexpected and unpredictable behavior may occur...", UserWarning)
        self._unload_plugins()
        self.collect_plugins()

    def _discover_plugins(self):
        self.state = State.DISCOVERING
        # for each plugin type
        for type_name in self.plugin_types.keys():

            # get all entrypoints matching that group
            group = entrypoints.get_group_named(f"xicam.plugins.{type_name}")
            group_all = entrypoints.get_group_all(f"xicam.plugins.{type_name}")

            # check for duplicate names
            self._check_shadows(group, group_all)

            for name, entrypoint in group.items():
                # If this entrypoint hasn't already been queued
                if entrypoint not in self._entrypoints[type_name] and entrypoint.name not in self._blacklist:
                    # ... queue and cache it
                    self._load_queue.put((type_name, entrypoint))
                    self._entrypoints[type_name][name] = entrypoint

            msg.logMessage(f"Discovered {type_name} entrypoints:", *self._entrypoints[type_name].values(), sep="\n")
        if self.state == State.DISCOVERING:
            self.state = State.LOADING

    @staticmethod
    def _check_shadows(group, group_all):
        # Warn the user if entrypoint names may shadow each other
        if len(group_all) != len(group):
            # There are some name collisions. Let's go digging for them.
            for name, matches in itertools.groupby(group_all, lambda ep: ep.name):
                matches = list(matches)
                if len(matches) != 1:
                    winner = group[name]
                    warnings.warn(
                        f"There are {len(matches)} conflicting entrypoints which share the name {name!r}:\n{matches}\n"
                        f"Loading entrypoint from {winner.module_name} and ignoring others."
                    )

    @threads.method(
        threadkey="entrypoint-loader", showBusy=False, cancelIfRunning=False
    )  # progress state managed independently
    def _load_plugins(self):
        started_instantiating = False

        # For every entrypoint in the load queue
        while not self._load_queue.empty():
            type_name, entrypoint = self._load_queue.get()

            # load it
            self._load_plugin(type_name, entrypoint)

            if not started_instantiating:  # If this is the first load
                # Start an event chain to pull from the queue
                threads.invoke_as_event(self._instantiate_plugin)
                started_instantiating = True

            # mark it as completed
            self._load_queue.task_done()

        # Finished loading, progress
        if self.state == State.LOADING:
            self.state = State.INSTANTIATING

    def _load_plugin(self, type_name, entrypoint: entrypoints.EntryPoint):
        # if the entrypoint was already loaded into cache and queued, do nothing
        if self._load_cache[type_name].get(entrypoint.name, None):
            return

        try:
            # Load the entrypoint (unless already cached), cache it, and put it on the instantiate queue
            msg.logMessage(f"Loading entrypoint {entrypoint.name} from module: {entrypoint.module_name}")
            with load_timer() as elapsed:
                plugin_class = self._load_cache[type_name][entrypoint.name] = (
                    self._load_cache[type_name].get(entrypoint.name, None) or entrypoint.load()
                )
        except (Exception, SystemError) as ex:
            msg.logMessage(f"Unable to load {entrypoint.name} plugin from module: {entrypoint.module_name}", msg.ERROR)
            msg.logError(ex)
            msg.notifyMessage(
                repr(ex), title=f'An error occurred while starting the "{entrypoint.name}" plugin.', level=msg.CRITICAL
            )

        else:
            msg.logMessage(f"{int(elapsed() * 1000)} ms elapsed while loading {entrypoint.name}", level=msg.INFO)
            self._instantiate_queue.put((type_name, entrypoint, plugin_class))

    def _instantiate_plugin(self):
        if not self._instantiate_queue.empty():
            type_name, entrypoint, plugin_class = self._instantiate_queue.get()

            # if this plugin was already instantiated earlier, skip it; mark done
            if self.type_mapping[type_name].get(entrypoint.name, None) is None:

                # inject the entrypoint name into the class
                plugin_class._name = entrypoint.name

                success = False

                # ... and instantiate it (as long as its supposed to be singleton)

                try:
                    if getattr(plugin_class, "is_singleton", False):
                        msg.logMessage(f"Instantiating {entrypoint.name} plugin object.", level=msg.INFO)
                        with load_timer() as elapsed:
                            self.type_mapping[type_name][entrypoint.name] = plugin_class()

                        msg.logMessage(
                            f"{int(elapsed() * 1000)} ms elapsed while instantiating {entrypoint.name}", level=msg.INFO
                        )
                    else:
                        self.type_mapping[type_name][entrypoint.name] = plugin_class
                    success = True

                except (Exception, SystemError) as ex:
                    msg.logMessage(
                        f"Unable to instantiate {entrypoint.name} plugin from module: {entrypoint.module_name}", msg.ERROR
                    )
                    msg.logError(ex)
                    msg.notifyMessage(repr(ex), title=f'An error occurred while starting the "{entrypoint.name}" plugin.')

                if success:
                    msg.logMessage(f"Successfully collected {entrypoint.name} plugin.", level=msg.INFO)
                    msg.showProgress(self._progress_count(), maxval=self._entrypoint_count())
                    self._notify(Filters.UPDATE)

            # mark it as completed
            self._instantiate_queue.task_done()

        # If this was the last plugin
        if self._load_queue.empty() and self._instantiate_queue.empty() and self.state in [State.INSTANTIATING, State.READY]:
            self.state = State.READY
            msg.logMessage("Plugin collection completed!")
            msg.hideProgress()
            self._notify(Filters.COMPLETE)

        if not self.state == State.READY:  # if we haven't reached the last task, but there's nothing queued
            threads.invoke_as_event(self._instantiate_plugin)  # return to the event loop, but come back soon

    def _get_plugin_by_name(self, name, type_name):
        return_plugin = None
        # Check all types matching type_name
        for search_type_name in self.plugin_types.keys():
            if type_name == search_type_name or not type_name:
                match_plugin = self.type_mapping[search_type_name].get(name, None)
                if match_plugin and return_plugin:
                    raise ValueError(
                        "Multiple plugins with the same name but different types exist. " "Must specify type_name."
                    )
                return_plugin = match_plugin

        return return_plugin

    def _get_entrypoint_by_name(self, name, type_name):
        return_entrypoint = None
        return_type = None
        # Check all types matching type_name
        for search_type_name in self.plugin_types.keys():
            if type_name == search_type_name or not type_name:
                match_entrypoint = self._entrypoints[search_type_name].get(name, None)
                if match_entrypoint and return_entrypoint:
                    raise ValueError(
                        "Multiple plugins with the same name but different types exist. " "Must specify type_name."
                    )
                return_entrypoint = match_entrypoint
                return_type = search_type_name

        return return_entrypoint, return_type

    def get_plugin_by_name(self, name, type_name=None, timeout=10):
        """
        Find a collected plugin named `name`, optionally by also specifying the type of plugin.

        Parameters
        ----------
        name : str
            name of the plugin to get
        type_name : str
            type of the plugin to get (optional)

        Returns
        -------
        object
            the matching plugin object (may be a class or instance), or None if not found
        """
        return_plugin = self._get_plugin_by_name(name, type_name)

        if return_plugin:
            return return_plugin

        # If still actively collecting plugins
        if self.state != State.READY:
            # find the matching entrypoint
            entrypoint, type_name = self._get_entrypoint_by_name(name, type_name)

            if not entrypoint:
                raise NameError(
                    f"The plugin named {name} of type {type_name} could not be discovered. "
                    f"Check your installation integrity."
                )

            # Load it immediately; it will move to top of instantiate queue as well
            msg.logMessage(f"Immediately loading {entrypoint.name}.", level=msg.INFO)
            self._load_plugin(type_name, entrypoint)

            # Add another instantiate event to the Qt event queue, so that it triggers in the next event loop
            threads.invoke_as_event(self._instantiate_plugin)

            # wait for it to load
            with load_timer() as elapsed:
                while not return_plugin:
                    return_plugin = self._get_plugin_by_name(name, type_name)
                    if threads.is_main_thread():
                        from qtpy.QtWidgets import QApplication  # Required as late import to avoid loading Qt things too soon
                        QApplication.processEvents()
                    else:
                        time.sleep(0.01)
                    if elapsed() > timeout:
                        raise TimeoutError(f"Plugin named {name} waited too long to instantiate and timed out")

        return return_plugin

    def get_plugins_of_type(self, type_name):
        return list(self.type_mapping[type_name].values())

    def attach(self, callback, filter=None):
        """
        Subscribe a callback to receive notifications. If a filter is used, only matching notifications are sent.
        See `Filters` for options.

        """
        self._observers.append((callback, filter))

    def _notify(self, filter=None):
        """ Notify all observers. Observers attached with filters much mach the emitted filter to be notified."""
        for callback, obsfilter in self._observers:
            if obsfilter == filter or not obsfilter:
                callback()

    def venvChanged(self):
        self.collect_plugins()

    def _entrypoint_count(self):
        return sum(map(len, self._entrypoints.values()))

    def _progress_count(self):
        return sum(map(len, self.type_mapping.values()))

    def getPluginsOfCategory(self, type_name):
        raise NotImplementedError("This method has been renamed to follow snake_case")
        warnings.warn("Transition to snake_case in progress...", DeprecationWarning)
        return self.get_plugins_of_type(type_name)

    def collectPlugins(self):
        raise NotImplementedError("This method has been renamed to follow snake_case")
        warnings.warn("Transition to snake_case in progress...", DeprecationWarning)
        return self.collect_plugins()

    def getPluginByName(self, plugin_name, type_name):
        raise NotImplementedError("This method has been renamed to follow snake_case")
        warnings.warn("Transition to snake_case in progress...", DeprecationWarning)
        return self.get_plugin_by_name(plugin_name, type_name)


# Setup plugin manager
manager = XicamPluginManager()


# A light class to mimic EntryPoint for live objects
class LiveEntryPoint(entrypoints.EntryPoint):
    def __init__(self, name, object, extras=None, distro=None):
        super(LiveEntryPoint, self).__init__(
            name, module_name="[live]", object_name=object.__name__, extras=extras, distro=distro
        )
        self.object = object

    def load(self):
        return self.object


from ._version import get_versions

__version__ = get_versions()["version"]
del get_versions
