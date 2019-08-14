import sys
import os
import platform
from pathlib import Path

from appdirs import user_config_dir, site_config_dir, user_cache_dir
from yapsy import PluginInfo
from yapsy.PluginManager import PluginManager

from xicam.core import msg
from .DataHandlerPlugin import DataHandlerPlugin
from .GUIPlugin import GUIPlugin, GUILayout
from .ProcessingPlugin import ProcessingPlugin, EZProcessingPlugin, Input, Output, InOut, InputOutput
from .SettingsPlugin import SettingsPlugin, ParameterSettingsPlugin
from .DataResourcePlugin import DataResourcePlugin
from .ControllerPlugin import ControllerPlugin
from .WidgetPlugin import QWidgetPlugin
from .venvs import observers as venvsobservers
from .DataResourcePlugin import DataResourcePlugin
from .FittableModelPlugin import Fittable1DModelPlugin
from .EZPlugin import _EZPlugin, EZPlugin
from .hints import PlotHint, Hint
from yapsy.PluginManager import NormalizePluginNameForModuleName, imp, log
import xicam
import importlib.util
from collections import deque
from contextlib import contextmanager
from timeit import default_timer
from xicam.core import threads
import time

op_sys = platform.system()
if op_sys == 'Darwin':  # User config dir incompatible with venv on darwin (space in path name conflicts)
    user_plugin_dir = os.path.join(user_cache_dir(appname='xicam'), 'plugins')
else:
    user_plugin_dir = os.path.join(user_config_dir(appname='xicam'), 'plugins')
site_plugin_dir = os.path.join(site_config_dir(appname='xicam'), 'plugins')

qt_is_safe = False
if 'qtpy' in sys.modules:
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


class XicamPluginManager(PluginManager):
    def __init__(self):
        super(XicamPluginManager, self).__init__()
        venvsobservers.append(self)

        # Link categories to base classes
        categoriesfilter = {'DataHandlerPlugin': DataHandlerPlugin,
                            'DataResourcePlugin': DataResourcePlugin,
                            'ProcessingPlugin': ProcessingPlugin,
                            'Fittable1DModelPlugin': Fittable1DModelPlugin,
                            }

        # If xicam.gui is not loaded (running headless), don't load GUIPlugins or WidgetPlugins
        if qt_is_safe:
            categoriesfilter.update({'ControllerPlugin': ControllerPlugin,
                                     'GUIPlugin': GUIPlugin,
                                     'WidgetPlugin': QWidgetPlugin,
                                     'SettingsPlugin': SettingsPlugin,
                                     'EZPlugin': _EZPlugin,
                                     'Fittable1DModelPlugin': Fittable1DModelPlugin})

        self.setCategoriesFilter(categoriesfilter)

        # Places to look for plugins
        self.plugindirs = [user_plugin_dir,
                           site_plugin_dir] \
                          + list(xicam.__path__)
        self.setPluginPlaces(self.plugindirs)
        msg.logMessage('plugindirectories:', *self.plugindirs)

        # Loader thread
        self.loadthread = None
        self.loadqueue = deque()

        self.observers = []

        self.loading = False
        self.loadcomplete = False

    def attach(self, callback, filter=None):
        self.observers.append((callback, filter))

    def notify(self, filter=None):
        for callback, obsfilter in self.observers:
            callback()


    def loading_except_slot(self, ex):
        msg.logError(ex)
        raise NameError(f'No plugin named {name} is in the queue or plugin manager.')

    def getPluginByName(self, name, category="Default", timeout=150):
        plugin = super(XicamPluginManager, self).getPluginByName(name, category)

        if plugin:
            with load_timer() as elapsed:
                while not plugin.plugin_object:
                    # the plugin was loaded, but the instanciation event hasn't fired yet
                    if threads.is_main_thread():
                        QApplication.processEvents()
                    else:
                        time.sleep(.01)
                    if elapsed() > timeout:
                        raise TimeoutError(f'Plugin named {name} waited too long to instanciate')
            return plugin

        # if queueing
        if len(self.loadqueue):
            for load_item in list(self.loadqueue):
                if load_item[2].name == name:
                    self.loadqueue.remove(load_item)  # remove the item from the top-level queue
                    msg.logMessage(f'Immediately loading {load_item[2].name}.', level=msg.INFO)
                    self.load_plugin(*load_item)  # and load it immediately
                    break

            # Run a wait loop until the plugin element is instanciated by main thread
            with load_timer() as elapsed:
                while (not plugin) or (not plugin.plugin_object):
                    plugin = super(XicamPluginManager, self).getPluginByName(name, category)
                    if threads.is_main_thread():
                        QApplication.processEvents()
                    else:
                        time.sleep(.01)
                    if elapsed() > timeout:
                        raise TimeoutError(f'Plugin named {name} waited too long to instanciate')

        return plugin

    def getPluginsOfCategory(self, category_name):
        plugins = super(XicamPluginManager, self).getPluginsOfCategory(category_name)
        return [plugin for plugin in plugins if plugin.plugin_object]

    def collectPlugins(self, paths=None):
        """
        Walk through the plugins' places and look for plugins.  Then
        for each plugin candidate look for its category, load it and
        stores it in the appropriate slot of the category_mapping.

        Overloaded to add callback.
        """
        self.loading = True

        self.setPluginPlaces(self.plugindirs + (paths or []))

        self.locatePlugins()

        # Prevent loading two plugins with the same name
        candidatedict = {c[2].name: c[2] for c in self._candidates}
        candidatesset = candidatedict.values()

        for plugin in reversed(self._candidates):
            if plugin[2] not in candidatesset:
                msg.logMessage(f'Possible duplicate plugin name "{plugin[2].name}" at {plugin[2].path}',
                               level=msg.WARNING)
                msg.logMessage(f'Possibly shadowed by {candidatedict[plugin[2].name].path}', level=msg.WARNING)
                self._candidates.remove(plugin)

        msg.logMessage('Candidates:')
        for candidate in self._candidates: msg.logMessage(candidate)

        future = threads.QThreadFutureIterator(self.loadPlugins,
                                               callback_slot=self.showLoading,
                                               finished_slot=lambda: setattr(self, 'loadcomplete', True))
        future.start()

        self.notify()

    def instanciatePlugin(self, plugin_info, element):
        '''
        The default behavior is that each plugin is instanciated at load time; the class is thrown away.
        Add the isSingleton = False attribute to your plugin class to prevent this behavior!
        '''
        msg.logMessage(f'Instanciating {plugin_info.name} plugin object.')

        with load_timer() as elapsed:
            try:
                if getattr(element, 'isSingleton', True):
                    plugin_info.plugin_object = element()
                else:
                    plugin_info.plugin_object = element
            except (Exception, SystemError) as ex:
                exc_info = sys.exc_info()
                msg.logMessage("Unable to instanciate plugin: %s" % plugin_info.path, msg.ERROR)
                msg.logError(ex)
                msg.notifyMessage(repr(ex),
                                  title=f'An error occurred while starting the "{plugin_info.name}" plugin.',
                                  level=msg.CRITICAL)
                plugin_info.error = exc_info

        msg.logMessage(f'{int(elapsed()*1000)} ms elapsed while instanciating {plugin_info.name}',
                       level=msg.INFO)

        self.notify()

    def showLoading(self, plugininfo: PluginInfo):
        # Indicate loading status
        name = plugininfo.name
        msg.logMessage(f'Loading {name} from {plugininfo.path}')

    def venvChanged(self):
        self.setPluginPlaces([venvs.current_environment])
        self.collectPlugins()

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
        if not hasattr(self, '_candidates'):
            raise ValueError("locatePlugins must be called before loadPlugins")

        self.processed_plugins = []

        self.loadqueue.extend(self._candidates)

        initial_len = len(self.loadqueue)

        for candidate_infofile, candidate_filepath, plugin_info in iter(self.loadqueue.popleft, (None, None, None)):
            # yield a message can be displayed to the user
            yield plugin_info

            self.load_plugin(candidate_infofile=candidate_infofile, candidate_filepath=candidate_filepath,
                             plugin_info=plugin_info)

            msg.showProgress(initial_len - len(self.loadqueue), maxval=initial_len)

            if not len(self.loadqueue):
                break
        # Remove candidates list since we don't need them any more and
        # don't need to take up the space
        delattr(self, '_candidates')
        return self.processed_plugins

    def load_plugin(self, candidate_infofile, candidate_filepath, plugin_info):
        msg.logMessage(
            f'Loading {plugin_info.name} plugin in {"main" if threads.is_main_thread() else "background"} thread.',
            level=msg.INFO)
        # make sure to attribute a unique module name to the one
        # that is about to be loaded
        plugin_module_name_template = NormalizePluginNameForModuleName(  # why?
            "yapsy_loaded_plugin_" + plugin_info.name) + "_%d"

        # make a uniquely numbered module name; again, why?
        for plugin_name_suffix in range(len(sys.modules)):
            plugin_module_name = plugin_module_name_template % plugin_name_suffix
            if plugin_module_name not in sys.modules:
                break

        try:
            # use imp to correctly load the plugin as a module
            from importlib._bootstrap_external import _POPULATE

            submodule_search_locations = os.path.dirname(plugin_info.path) if plugin_info.path.endswith(
                "__init__.py") else _POPULATE

            spec = importlib.util.spec_from_file_location(plugin_info.name, plugin_info.path,
                                                          submodule_search_locations=submodule_search_locations)
            candidate_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(candidate_module)

        except Exception as ex:
            exc_info = sys.exc_info()
            msg.logMessage("Unable to import plugin: %s" % plugin_info.path, msg.ERROR)
            msg.logError(ex)
            msg.notifyMessage(repr(ex),
                              title=f'The "{plugin_info.name}" plugin could not be loaded.',
                              level=msg.CRITICAL)
            plugin_info.error = exc_info
            self.processed_plugins.append(plugin_info)
            return
        self.processed_plugins.append(plugin_info)

        if "__init__" in os.path.basename(plugin_info.name):  # is this necessary?
            print('Yes, it is?')
            sys.path.remove(plugin_info.path)
        # now try to find and initialise the first subclass of the correct plugin interface

        #### ADDED BY RP

        dirlist = dir(candidate_module)
        if hasattr(candidate_module, '__plugin_exports__'):
            dirlist = candidate_module.__plugin_exports__
        ####

        with load_timer() as elapsed:  # cm for load timing

            element_name = plugin_info.details['Core'].get('Object', None)  # Try explicitly defined element first

            success = False
            if element_name:
                element = getattr(candidate_module, element_name)
                success = self.load_element(element, candidate_infofile, plugin_info)

            if not success:
                for element in (getattr(candidate_module, name) for name in dirlist):  # add filtering?

                    self.load_element(element, candidate_infofile, plugin_info)

            if success:
                msg.logMessage(f'{int(elapsed() * 1000)} ms elapsed while loading {plugin_info.name}', level=msg.INFO)
            else:
                msg.logMessage(f'No plugin found in indicated module: {candidate_filepath}', msg.ERROR)

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

                        threads.invoke_in_main_thread(self.instanciatePlugin, plugin_info, element)


                    except Exception as ex:
                        exc_info = sys.exc_info()
                        msg.logError(ex)
                        msg.logMessage("Unable to create plugin object: %s" % plugin_info.path)
                        plugin_info.error = exc_info
                        # break  # If it didn't work once it wont again
                        raise RuntimeError('An error occurred while loading plugin: %s' % plugin_info.path)
                    else:
                        plugin_info.categories.append(current_category)
                        self.category_mapping[current_category].append(plugin_info)
                        self._category_file_mapping[current_category].append(candidate_infofile)

                        return True


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

__version__ = get_versions()['version']
del get_versions
