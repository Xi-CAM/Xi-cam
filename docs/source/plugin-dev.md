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