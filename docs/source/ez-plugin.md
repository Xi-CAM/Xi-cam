# Creating an EZPlugin

The EZPlugin function provides a way to create a custom GUI plugin, although the 
customization is somewhat limited. 

*If you are interested in developing a more customizable GUI plugin, see [Creating a GUIPlugin](gui-plugin.md).*

## Creating a Simple EZPlugin

In order to create an EZPlugin for Xi-cam, two files must be created and 
locatable by Xi-cam. The first file is responsible for creating the plugin
itself, and the second file is used to register the plugin with Xi-cam. This 
means that when Xi-cam starts, it will be able to find the plugin you created 
and load it.

### Implementing SimpleEZPlugin

To start, we can write a basic plugin, called `SimpleEZPlugin`.
We will need to create a python file that will create this plugin.
Create a new file, `SimpleEZPlugin.py` and add the following:

```python
import xicam.plugins

SimpleEZPlugin = EZPlugin(name='SimpleEZPlugin')

```

This code imports the `xicam.plugins` module so we can make use of its 
definitions and then creates a `SimpleEZPlugin`. Let's take a look 
at the documentation for this function (*note: after importing `xicam.plugins`, 
this documentation can be obtained using ```help(EZPlugin)```)*:

```eval_rst
.. autosimplefunction:: xicam.plugins.EZPlugin
```

All of the arguments to this function have default values, but we will want
to provide our own name for the plugin. So, we provide `name='SimpleEZPlugin'`.
This creates a new plugin type based on the `name`, in our case `SimpleEZPlugin`.

## Registering the SimpleEZPlugin

Now that we have provided code for our `SimpleEZPlugin`, we need a way to tell
Xi-cam to load this plugin. We will use a plugin info file, or *marker file*, to
do this. The marker file works by providing Xi-cam the name of the plugin to
load and where to find the plugin code. Marker files will have the 
extension `.yapsy-plugin`.

### Determining where to put the marker file

We can use the python interpreter and the `xicam.plugins` module to find out
where Xi-cam looks for its plugins. We will be using the `user_plugin_dir`
variable to register the `SimpleEZPlugin` on a *user-specific* level (i.e. 
the plugin will not be shared between users -- note that it is possible to
install the plugin on a shared system level). 
In a terminal, run the following code:

```python
python()

>>> import xicam.plugins
>>> xicam.plugins.user_plugin_dir
```

The user_plugin_dir should look one of the following:

* `~/.config/xicam/plugins` (Linux)
* `/Users/username/Library/Caches/xicam/plugins` (macOS)
* `C:\Users\username\AppData\Local\<AppAuthor>\xicam\plugins` (Windows)

**TODO `<AppAuthor>` in windows**

### Writing a plugin marker file

Create a `SimpleEZPlugin.yapsy-plugin` file in the location that
`user_plugin_dir` provides for your operating system with the following 
contents:

```
[Core]
Name = SimpleEZPlugin
Module = /path/to/SimpleEZPlugin.py

[Documentation]
Author = My Name
Version = 0.1.0
Website = http://mywebsite.somedomain
Description = My first plugin

```

The `[Core]` section tells Xi-cam both the name of the plugin to look for and
the location of the plugin's code.

## Running Xi-cam

**TODO: assume that the EZPlugin developer will be running Xi-cam via
`python run_xicam.py`.**

Now that we have created SimpleEZPlugin and have told Xi-cam where to find
SimpleEZPlugin, we can run Xi-cam:

```python
python run_xicam.py
```

Xi-cam will look through its plugin directories and it should find the
`SimpleEZPlugin.yapsy-plugin` file. It will then attempt to load the 
`SimpleEZPlugin`.

![TODO: Screenshot?](file:///Users/ian/repos/Xi-cam.gui/xicam/gui/static/icons/cake.png)

*Note: The message logger provided by Xi-cam can be useful for debugging 
problems with plugin loading*

