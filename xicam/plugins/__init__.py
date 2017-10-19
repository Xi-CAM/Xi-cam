from appdirs import user_config_dir, site_config_dir
from yapsy.IPlugin import IPlugin
from yapsy.PluginManager import PluginManager

user_plugin_dir = user_config_dir('xicam/plugins')
site_plugin_dir = site_config_dir('xicam/plugins')


class IGUIPlugin(IPlugin):
    pass


class IEZPlugin(IGUIPlugin):
    pass


class IProcessingPlugin(IPlugin):
    def activate(self):
        pass

    def deactivate(self):
        pass


class IVisualizationPlugin(IPlugin):
    pass


from .IFileFormatPlugin import IFileFormatPlugin


manager = PluginManager()
manager.setPluginPlaces([".", user_plugin_dir, site_plugin_dir])
manager.setCategoriesFilter({
    "EZPlugin": IEZPlugin,
    "GUIModePlugin": IGUIPlugin,
    "ProcessingPlugin": IProcessingPlugin,
    "Visualization": IVisualizationPlugin,
    "FileFormatPlugin": IFileFormatPlugin,
})
manager.collectPlugins()

# Loop round the plugins and print their names.
for plugin in manager.getAllPlugins():
    plugin.plugin_object.print_name()

# Loop over each "Visualization" plugin
for pluginInfo in manager.getPluginsOfCategory("Visualization"):
    pluginInfo.plugin_object.doSomething(...)
