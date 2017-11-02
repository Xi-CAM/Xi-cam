import os

from appdirs import user_config_dir, site_config_dir
from yapsy import PluginInfo
from yapsy.PluginManager import PluginManager

from xicam.core import msg
from .DataResourcePlugin import IDataResourcePlugin
from .FileFormatPlugin import IFileFormatPlugin
from .FittableModelPlugin import IFittable1DModelPlugin
from .GUIPlugin import IGUIPlugin, GUILayout
from .ProcessingPlugin import IProcessingPlugin

user_plugin_dir = user_config_dir('xicam/plugins')
site_plugin_dir = site_config_dir('xicam/plugins')


class XicamPluginManager(PluginManager):
    def collectPlugins(self):
        """
        Walk through the plugins' places and look for plugins.  Then
        for each plugin candidate look for its category, load it and
        stores it in the appropriate slot of the category_mapping.

        Overloaded to add callback.
        """

        self.locatePlugins()
        self.loadPlugins(callback=self.showLoading)

    def showLoading(self, plugininfo: PluginInfo):
        # Indicate loading status
        name = plugininfo.name
        msg.logMessage(f'Loading {name}')


# Setup plugin manager
manager = XicamPluginManager()
manager.setPluginPlaces([os.path.dirname(__file__), user_plugin_dir, site_plugin_dir])
manager.setCategoriesFilter({
    "GUIPlugin": IGUIPlugin,
    "ProcessingPlugin": IProcessingPlugin,
    "FileFormatPlugin": IFileFormatPlugin,
})

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
