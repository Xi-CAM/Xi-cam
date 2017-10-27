import os

from appdirs import user_config_dir, site_config_dir
from yapsy.PluginManager import PluginManager

from .IDataResourcePlugin import IDataResourcePlugin
from .IFileFormatPlugin import IFileFormatPlugin
from .IFittableModelPlugin import IFittable1DModelPlugin
from .IGUIPlugin import IGUIPlugin
from .IProcessingPlugin import IProcessingPlugin

user_plugin_dir = user_config_dir('xicam/plugins')
site_plugin_dir = site_config_dir('xicam/plugins')




manager = PluginManager()
manager.setPluginPlaces([os.path.dirname(__file__), user_plugin_dir, site_plugin_dir])
manager.setCategoriesFilter({
    "GUIPlugin": IGUIPlugin,
    "ProcessingPlugin": IProcessingPlugin,
    "FileFormatPlugin": IFileFormatPlugin,
})
manager.collectPlugins()

# # Loop round the plugins and print their names.
# for plugin in manager.getAllPlugins():
#     plugin.plugin_object.print_name()
#
# # Loop over each "Visualization" plugin
# for pluginInfo in manager.getPluginsOfCategory("Visualization"):
#     pluginInfo.plugin_object.doSomething(...)
