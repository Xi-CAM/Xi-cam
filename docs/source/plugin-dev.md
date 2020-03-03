# Creating a Plugin

*For a simpler way to create plugins, please see* [Creating an EZPlugin](ez-plugin.md).

For those more familiar with Python, it is possible to create more complex plugins by deriving a
plugin provided by the *xicam.plugins* module.


## Registering a plugin

After creating your plugin, you must register it using "Entry Points" so that Xi-cam 
can find it. Entry Points are a [Python packaging mechanism](https://packaging.python.org/specifications/entry-points/) 
allowing tools to discover pluggable components.

To define an entry point for your plugin, we add to the setup.py of your package.
For example, to define an entry point for a `GUIPlugin` class named `"my_plugin"` 
in the `xicam.awesomeplugin` module, we add:

```
setup(
    ...
    entry_points={
        'xicam.plugins.GUIPlugin': ['my_plugins_name = xicam.awesomeplugin:my_plugin',], 
    },
    ...
)
```
Multiple plugins can be defined in this way within the same Python package.

## User-specific vs. User-shared Plugins

When creating the yapsy info files, the plugin info files can be installed on a
user specific basis or a shared basis. Xi-cam will look for plugins in both
of these locations.

**TODO: replace user-specific with more appropriate term (or use synonymous 
definition)**

To see where these Xi-cam plugin directories are located, you can use the
following variables provided by the `xicam.plugins` module:

`xicam.plugins.user_plugin_dir`: path to the user Xi-cam plugin directory
 
`xicam.plugins.site_plugin_dir`: path to the shared Xi-cam plugin directory

*Q: what happens if you have XPlugin in both the user_plugin_dir and the
site_plugin_dir?*

*A: Xi-cam will first look in the user_plugin_dir. If there is a duplicate
plugin in the site_plugin_dir, then a warning will be logged about a possible
duplicate. The user_plugin_dir plugin will take precedence.*

