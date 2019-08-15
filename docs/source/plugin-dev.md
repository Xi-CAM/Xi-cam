# Creating a Plugin

*For a simpler way to create plugins, please see* [Creating an EZPlugin](ez-plugin.md).

For those more familiar with Python, it is possible to create more complex plugins by deriving a
plugin provided by the *xicam.plugins* module.


## Yapsy

**TODO: do we need a section on this?**


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

