import sys
import os
from pathlib import Path

from appdirs import user_config_dir, site_config_dir
from yapsy import PluginInfo
from yapsy.PluginManager import PluginManager

from xicam.core import msg
from .DataHandlerPlugin import DataHandlerPlugin
from .GUIPlugin import GUIPlugin, GUILayout
from .ProcessingPlugin import ProcessingPlugin, Input, Output
from .SettingsPlugin import SettingsPlugin
from .DataResourcePlugin import DataResourcePlugin
from .WidgetPlugin import QWidgetPlugin
from .venvs import observers as venvsobservers

user_plugin_dir = user_config_dir('xicam/plugins')
site_plugin_dir = site_config_dir('xicam/plugins')

# Observers will be notified when active plugins changes
observers = []

class XicamPluginManager(PluginManager):
    def __init__(self):
        super(XicamPluginManager, self).__init__()
        venvsobservers.append(self)

        # Link categories to base classes
        categoriesfilter = {'GUIPlugin': GUIPlugin,
                            'WidgetPlugin': QWidgetPlugin,
                            'SettingsPlugin': SettingsPlugin,
                            'DataHandlerPlugin': DataHandlerPlugin,
                            'DataResourcePlugin': DataResourcePlugin}

        # If xicam.gui is not loaded (running headless), don't load GUIPlugins or WidgetPlugins
        if 'xicam.gui' not in sys.modules:
            categoriesfilter['GUIPlugin'] = None
            categoriesfilter['WidgetPlugin'] = None
            categoriesfilter['SettingsPlugin'] = None

        self.setCategoriesFilter(categoriesfilter)

    def collectPlugins(self):
        """
        Walk through the plugins' places and look for plugins.  Then
        for each plugin candidate look for its category, load it and
        stores it in the appropriate slot of the category_mapping.

        Overloaded to add callback.
        """

        self.locatePlugins()

        # Prevent loading two plugins with the same name
        candidatesset = {c[2].name:c for c in self._candidates}.values()

        for plugin in self._candidates:
            if plugin[2] not in candidatesset:
                msg.logMessage(f'Possible duplicate plugin name "{plugin[2].name}"',level=msg.WARNING)

        self._candidates=candidatesset

        self.loadPlugins(callback=self.showLoading)

        self.instanciateLatePlugins()
        for observer in observers:
            observer.pluginsChanged()

    def instanciateLatePlugins(self):
        for plugin_info in self.getPluginsOfCategory('GUIPlugin'):
            if callable(plugin_info.plugin_object):
                try:
                    plugin_info.plugin_object = plugin_info.plugin_object()  # Force late singleton-ing of GUIPlugins
                except Exception as ex:
                    msg.notifyMessage(f'The "{plugin_info.name}" plugin could not be loaded. {repr(ex)}',
                                      level=msg.CRITICAL)
                    msg.logError(ex, ex, ex.__traceback__)

    def instanciateElement(self, element):
        '''
        The default behavior is that each plugin is instanciated at load time; the class is thrown away.
        Add the isSingleton = False attribute to your plugin class to prevent this behavior!
        '''
        if getattr(element, 'isSingleton', True):
            return element()
        return element

    def showLoading(self, plugininfo: PluginInfo):
        # Indicate loading status
        name = plugininfo.name
        msg.logMessage(f'Loading {name}')

    def venvChanged(self):
        self.setPluginPlaces([venvs.current_environment])
        self.collectPlugins()



# Setup plugin manager
manager = XicamPluginManager()
manager.setPluginPlaces(
    [os.getcwd(), str(Path(__file__).parent.parent), user_plugin_dir, site_plugin_dir, venvs.current_environment])

# Collect all the plugins
manager.collectPlugins()

# Example usage:
#
# # Loop round the plugins and print their names.
# for plugin in manager.getAllPlugins():
#     plugin.plugin_object.print_name()
#
# # Loop over each "Visualization" plugin
# for pluginInfo in manager.getPluginsOfCategory("Visualization"):
#     pluginInfo.plugin_object.doSomething(...)
