import os

from appdirs import user_config_dir, site_config_dir
from yapsy import PluginInfo
from yapsy.PluginManager import PluginManager

from xicam.core import msg
from .DataResourcePlugin import IDataResourcePlugin
from .FileFormatPlugin import IFileFormatPlugin
from .FittableModelPlugin import IFittable1DModelPlugin
from .GUIPlugin import GUIPlugin, GUILayout
from .ProcessingPlugin import IProcessingPlugin
from .venvs import observers as venvsobservers

user_plugin_dir = user_config_dir('xicam/plugins')
site_plugin_dir = site_config_dir('xicam/plugins')

# Observers will be notified when active plugins changes
observers = []

class XicamPluginManager(PluginManager):
    def __init__(self):
        super(XicamPluginManager, self).__init__()
        venvsobservers.append(self)

    def collectPlugins(self):
        """
        Walk through the plugins' places and look for plugins.  Then
        for each plugin candidate look for its category, load it and
        stores it in the appropriate slot of the category_mapping.

        Overloaded to add callback.
        """

        self.locatePlugins()
        self.loadPlugins(callback=self.showLoading)

        for observer in observers:
            observer.pluginsChanged()

    def showLoading(self, plugininfo: PluginInfo):
        # Indicate loading status
        name = plugininfo.name
        msg.logMessage(f'Loading {name}')

    def venvChanged(self):
        self.setPluginPlaces([venvs.current_environment])
        self.collectPlugins()



# Setup plugin manager
manager = XicamPluginManager()
manager.setPluginPlaces([os.path.dirname(__file__), user_plugin_dir, site_plugin_dir, venvs.current_environment])
manager.setCategoriesFilter({
    "GUIPlugin": GUIPlugin,
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
