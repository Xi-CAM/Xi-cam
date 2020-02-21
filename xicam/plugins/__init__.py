import sys
import os
import platform
import pkg_resources
import itertools
import warnings

import entrypoints
from appdirs import user_config_dir, site_config_dir, user_cache_dir
from yapsy import PluginInfo
from yapsy.PluginManager import PluginManager

import xicam
from xicam.core import msg
from xicam.core import threads
from xicam.core.args import parse_args

from .datahandlerplugin import DataHandlerPlugin
from .catalogplugin import CatalogPlugin
from .guiplugin import GUIPlugin, GUILayout
from .processingplugin import ProcessingPlugin, EZProcessingPlugin, Input, Output, InOut, InputOutput
from .settingsplugin import SettingsPlugin, ParameterSettingsPlugin
from .dataresourceplugin import DataResourcePlugin
from .controllerplugin import ControllerPlugin
from .widgetplugin import QWidgetPlugin

try:
    # try to find the venvs entrypoint
    if 'cammart' in entrypoints.get_group_named(f'xicam.plugins.SettingsPlugin') and not '--no-cammart' in sys.argv:
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

from yapsy.PluginManager import NormalizePluginNameForModuleName, imp, log
import importlib.util
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

qt_is_safe = False
if "qtpy" in sys.modules:
    from qtpy.QtWidgets import QApplication

    if QApplication.instance():
        qt_is_safe = True


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


class XicamPluginManager():
    def __init__(self):

        self._blacklist = []
        self._load_queue = LifoQueue()
        self._instantiate_queue = LifoQueue()
        self._entrypoints = {}
        self._load_cache = {}
        self._observers = []
        self.state = State.READY
        self.plugins = []
        self.type_mapping = {}
        self.plugin_types = {}

        # Observe changes to venvs
        if venvsobservers is not None:
            venvsobservers.append(self)

        # Load plugin types
        plugin_types = {ep.name: ep.load() for ep in entrypoints.get_group_named('xicam.plugins.PluginType')}

        # Toss plugin types that need qt if running without qt
        if not qt_is_safe:
            plugin_types = {type_name: type_class for type_name, type_class in plugin_types if
                            not getattr(type_class, 'needs_qt', True)}

        # Initialize types
        self.type_mapping = {type_name: {} for type_name in plugin_types.keys()}
        self._entrypoints = self.type_mapping.copy()
        self._load_cache = self.type_mapping.copy()

        # Check if cammart should be ignored
        try:
            args = parse_args(exit_on_fail=False)
            include_cammart = not args.nocammart
        except RuntimeError:
            include_cammart = False

        # ...if so, blacklist it
        if not include_cammart:
            self._blacklist.extend(['cammart', 'venvs'])

    def collect_plugins(self):
        """
        Find, load, and instantiate all Xi-cam plugins matching known plugin types

        """
        # If the pm is already collecting, just add new items to the queue
        discover_only = self.state == State.READY

        self.state = State.DISCOVERING
        self._discover_plugins()
        self.state = State.LOADING
        if not discover_only:
            self._load_plugins()

    def _discover_plugins(self):
        # for each plugin type
        for type_name in self.plugin_types.keys():

            # get all entrypoints matching that group
            group = entrypoints.get_group_named(f'xicam.plugins.{type_name}')
            group_all = entrypoints.get_group_all(f'xicam.plugins.{type_name}')

            # check for duplicate names
            self._check_shadows(group, group_all)

            for entrypoint in group:
                if entrypoint not in self._entrypoints[type_name]:  # If this entrypoint hasn't already been queued
                    # ... queue and cache it
                    self._load_queue.put((type_name, entrypoint))
                    self._entrypoints[type_name][entrypoint.name] = entrypoint

            msg.logMessage("Discovered entrypoints:", self._entrypoints)

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
                        f"There are {len(matches)} conflicting entrypoints which share the name {name!r}:\n{matches}"
                        f"Loading entrypoint from {winner.module_name} and ignoring others.")

    @threads.method(threadkey='entrypoint-loader')
    def _load_plugins(self):
        started_instantiating = False

        # For every entrypoint in the load queue
        for type_name, entrypoint in iter(self._load_queue.get, None):
            # load it
            self._load_plugin(type_name, entrypoint)

            if not started_instantiating:  # If this is the first load
                # Start an event chain to pull from the queue
                threads.invoke_as_event(self._instantiate_plugin)
                started_instantiating = True

            # mark it as completed
            self._load_queue.task_done()

            if self._load_queue.empty():  # Finished loading
                self.state = State.INSTANTIATING
                return

    def _load_plugin(self, type_name, entrypoint: entrypoints.EntryPoint):
        try:
            # Load the entrypoint (unless already cached), cache it, and put it on the instantiate queue
            msg.logMessage(f'Loading entrypoint {entrypoint.name} from module: {entrypoint.module_name}')
            with load_timer() as elapsed:
                plugin_class = self._load_cache[type_name][entrypoint.name] = \
                    self._load_cache[type_name].get(entrypoint.name, None) or entrypoint.load()
        except (Exception, SystemError) as ex:
            msg.logMessage(f"Unable to load {entrypoint.name} plugin from module: {entrypoint.module_name}", msg.ERROR)
            msg.logError(ex)
            msg.notifyMessage(
                repr(ex), title=f'An error occurred while starting the "{entrypoint.name}" plugin.', level=msg.CRITICAL
            )

        else:
            msg.logMessage(f"{int(elapsed() * 1000)} ms elapsed while instantiating {entrypoint.name}",
                           level=msg.INFO)
            self._instantiate_queue.put((type_name, entrypoint, plugin_class))

    def _instantiate_plugin(self):
        if not self._instantiate_queue.empty():  # If there's a task in the queue
            # ...get it
            type_name, entrypoint, plugin_class = self._instantiate_queue.get()

            # ... and instantiate it (as long as its supposed to be singleton)
            if not getattr(plugin_class, 'is_singleton', False):
                msg.logMessage(f"Instantiating {entrypoint.name} plugin object.", level=msg.INFO)
                try:
                    with load_timer() as elapsed:
                        self.type_mapping[type_name][entrypoint.name] = plugin_class()
                except (Exception, SystemError) as ex:
                    msg.logMessage(
                        f"Unable to instantiate {entrypoint.name} plugin from module: {entrypoint.module_name}",
                        msg.ERROR)
                    msg.logError(ex)
                    msg.notifyMessage(repr(ex),
                                      title=f'An error occurred while starting the "{entrypoint.name}" plugin.')

            else:
                self.type_mapping[type_name][entrypoint.name] = plugin_class

            msg.logMessage(f"Successfully collected {entrypoint.name} plugin.", level=msg.INFO)
            self._notify_on_schedule()

            # mark it as completed
            self._instantiate_queue.task_done()

            if self._instantiate_queue.empty() and self.state == State.INSTANTIATING:  # If this was the last plugin
                self.state = State.READY

        if not self.state == State.READY:  # if we haven't reached the last task, but there's nothing queued
            threads.invoke_as_event(self._instantiate_plugin)  # return to the event loop, but come back soon

    def _get_plugin_by_name(self, name, type_name):
        return_plugin = None
        # Check all types matching type_name
        for search_type_name in self.plugin_types.keys():
            if type_name == search_type_name or not type_name:
                match_plugin = self.type_mapping[search_type_name][name]
                if match_plugin and return_plugin:
                    raise NameError('Multiple plugins with the same name but different types exist. '
                                    'Must specify type_name.')
                return_plugin = match_plugin

        return return_plugin

    def _get_entrypoint_by_name(self, name, type_name):
        return_entrypoint = None
        return_type = None
        # Check all types matching type_name
        for search_type_name in self.plugin_types.keys():
            if type_name == search_type_name or not type_name:
                match_entrypoint = self._entrypoints[search_type_name][name]
                if match_entrypoint and return_entrypoint:
                    raise NameError('Multiple plugins with the same name but different types exist. '
                                    'Must specify type_name.')
                return_entrypoint = match_entrypoint
                return_type = search_type_name

        return return_entrypoint, return_type

    def get_plugin_by_name(self, name, type_name=None, timeout=3):
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
                raise NameError(f'The plugin named {name} of type {type_name} could not be discovered. '
                                f'Check your installation integrity.')

            # Load it immediately; it will move to top of instantiate queue as well
            msg.logMessage(f"Immediately loading {entrypoint.name}.", level=msg.INFO)
            self._load_plugin(type_name, entrypoint)

            # wait for it to load
            with load_timer() as elapsed:
                while not return_plugin:
                    return_plugin = self._get_plugin_by_name(name, type_name)
                    if threads.is_main_thread():
                        QApplication.processEvents()  #
                    else:
                        time.sleep(0.01)
                    if elapsed() > timeout:
                        raise TimeoutError(f"Plugin named {name} waited too long to instantiate and timed out")

        return return_plugin

    def attach(self, callback, filter=None):
        """ Ask to receive updates whenever new plugins are collected. """
        self.observers.append((callback, filter))

    def _notify_on_schedule(self, filter=None):
        """ Notify all observers IF we haven't recently """

    def _notify(self, filter=None):
        """ Notify all observers of new plugins"""
        for callback, obsfilter in self._observers:
            callback()

    def venvChanged(self):
        self.collect_plugins()

    def __getitem__(self, item: str):
        """
        Convenient way to get plugins.

        Usage
        -----

        manager['GUIPlugin']['SAXS']

        """
        return {plugin.name: plugin for plugin in self.getPluginsOfCategory(item)}

    def loadPlugins(self):
        """
        Load the candidate plugins that have been identified through a
        previous call to locatePlugins.  For each plugin candidate
        look for its category, load it and store it in the appropriate
        slot of the ``category_mapping``.

        If a callback function is specified, call it before every load
        attempt.  The ``plugin_info`` instance is passed as an argument to
        the callback.
        """
        # 		print "%s.loadPlugins" % self.__class__
        if not hasattr(self, "_candidates"):
            raise ValueError("locatePlugins must be called before loadPlugins")

        self.processed_plugins = []


        initial_len = len(self.loadqueue)

        for candidate_infofile, candidate_filepath, plugin_info in iter(self.loadqueue.popleft, (None, None, None)):
            self._loading_plugins.append(plugin_info)
            # yield a message can be displayed to the user
            yield plugin_info

            self.load_plugin(candidate_infofile, candidate_filepath, plugin_info)

            msg.showProgress(initial_len - len(self.loadqueue), maxval=initial_len)

            if not len(self.loadqueue):
                break
        # Remove candidates list since we don't need them any more and
        # don't need to take up the space
        delattr(self, "_candidates")

        return self.processed_plugins

    def load_plugin(self, candidate_infofile, candidate_filepath, plugin_info):
        if candidate_infofile:  # Yapsy-style plugin
            self.load_marked_plugin(
                candidate_infofile=candidate_infofile, candidate_filepath=candidate_filepath, plugin_info=plugin_info
            )
        else:  # EntryPoint style plugin
            # (entrypoints can't have more than one category)
            self.load_element_entry_point(plugin_info.categories[0], plugin_info)

    def load_marked_plugin(self, candidate_infofile, candidate_filepath, plugin_info):
        msg.logMessage(
            f'Loading {plugin_info.name} plugin in {"main" if threads.is_main_thread() else "background"} thread.',
            level=msg.INFO,
        )
        # make sure to attribute a unique module name to the one
        # that is about to be loaded
        plugin_module_name_template = (
            NormalizePluginNameForModuleName("yapsy_loaded_plugin_" + plugin_info.name) + "_%d"  # why?
        )

        # make a uniquely numbered module name; again, why?
        for plugin_name_suffix in range(len(sys.modules)):
            plugin_module_name = plugin_module_name_template % plugin_name_suffix
            if plugin_module_name not in sys.modules:
                break

        try:
            # use imp to correctly load the plugin as a module
            from importlib._bootstrap_external import _POPULATE

            submodule_search_locations = (
                os.path.dirname(plugin_info.path) if plugin_info.path.endswith("__init__.py") else _POPULATE
            )

            spec = importlib.util.spec_from_file_location(
                plugin_info.name, plugin_info.path, submodule_search_locations=submodule_search_locations
            )
            candidate_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(candidate_module)

        except Exception as ex:
            exc_info = sys.exc_info()
            msg.logMessage("Unable to import plugin: %s" % plugin_info.path, msg.ERROR)
            msg.logError(ex)
            msg.notifyMessage(repr(ex), title=f'The "{plugin_info.name}" plugin could not be loaded.', level=msg.CRITICAL)
            plugin_info.error = exc_info
            self.processed_plugins.append(plugin_info)
            return
        self.processed_plugins.append(plugin_info)

        if "__init__" in os.path.basename(plugin_info.name):  # is this necessary?
            print("Yes, it is?")
            sys.path.remove(plugin_info.path)
        # now try to find and initialise the first subclass of the correct plugin interface

        #### ADDED BY RP

        dirlist = dir(candidate_module)
        if hasattr(candidate_module, "__plugin_exports__"):
            dirlist = candidate_module.__plugin_exports__
        ####

        with load_timer() as elapsed:  # cm for load timing

            element_name = plugin_info.details["Core"].get("Object", None)  # Try explicitly defined element first

            success = False
            if element_name:
                element = getattr(candidate_module, element_name)
                success = self.load_element(element, candidate_infofile, plugin_info)

            if not success:
                for element in (getattr(candidate_module, name) for name in dirlist):  # add filtering?

                    success = self.load_element(element, candidate_infofile, plugin_info)
                    if success:
                        break
            if success:
                msg.logMessage(f"{int(elapsed() * 1000)} ms elapsed while loading {plugin_info.name}", level=msg.INFO)
            else:
                msg.logMessage(f"No plugin found in indicated module: {candidate_filepath}", msg.ERROR)

    def load_element_entry_point(self, category_name, plugin_info):
        """

        Parameters
        ----------
        element
        candidate_infofile
        plugin_info

        Returns
        -------
        bool
            True if the element matched a category, and will be accepted as a plugin

        """
        target_plugin_info = None

        element = plugin_info.plugin_object

        if element is not self.categories_interfaces[category_name]:  # don't try to instanciate bases
            # we found a new plugin: initialise it and search for the next one
            try:

                threads.invoke_in_main_thread(self.instanciatePlugin, plugin_info, element, category_name)

            except Exception as ex:
                exc_info = sys.exc_info()
                msg.logError(ex)
                msg.logMessage("Unable to create plugin object: %s" % plugin_info.path)
                plugin_info.error = exc_info
                # break  # If it didn't work once it wont again
                msg.logError(RuntimeError("An error occurred while loading plugin: %s" % plugin_info.path))
            else:
                # plugin_info.categories.append(category_name)
                # self.category_mapping[category_name].append(plugin_info)

                return True

    def load_element(self, element, candidate_infofile, plugin_info):
        """

        Parameters
        ----------
        element
        candidate_infofile
        plugin_info

        Returns
        -------
        bool
            True if the element matched a category, and will be accepted as a plugin

        """
        target_plugin_info = None
        for category_name in self.categories_interfaces:
            try:
                is_correct_subclass = issubclass(element, self.categories_interfaces[category_name])
            except Exception:
                continue
            if is_correct_subclass and element is not self.categories_interfaces[category_name]:
                current_category = category_name
                if candidate_infofile not in self._category_file_mapping[current_category]:
                    # we found a new plugin: initialise it and search for the next one
                    try:

                        threads.invoke_in_main_thread(self.instanciatePlugin, plugin_info, element, current_category)

                    except Exception as ex:
                        exc_info = sys.exc_info()
                        msg.logError(ex)
                        msg.logMessage("Unable to create plugin object: %s" % plugin_info.path)
                        plugin_info.error = exc_info
                        # break  # If it didn't work once it wont again
                        msg.logError(RuntimeError("An error occurred while loading plugin: %s" % plugin_info.path))
                    else:
                        # plugin_info.categories.append(current_category)
                        # self.category_mapping[current_category].append(plugin_info)
                        self._category_file_mapping[current_category].append(candidate_infofile)

                        return True


class EntryPointPluginInfo():
    def __init__(self, entry_point: entrypoints.EntryPoint, category_name):
        self.entry_point = entry_point
        self.plugin_object = None
        try:
            self.plugin_object = entry_point.load()
        except Exception as ex:
            msg.logError(ex)
        self.name = entry_point.name
        self.categories = [category_name]
        self.path = entry_point.module_name


# Setup plugin manager
manager = XicamPluginManager()

# Example usage:
#
# # Loop round the plugins and print their names.
# for plugin in manager.getAllPlugins():
#     plugin.plugin_object.print_name()
#
# # Loop over each "Visualization" plugin
# for pluginInfo in manager.getPluginsOfCategory("Visualization"):
#     pluginInfo.plugin_object.doSomething(...)

from ._version import get_versions

__version__ = get_versions()["version"]
del get_versions
