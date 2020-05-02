# QuickStart Guide

This is a quick-start guide that will help you install Xi-CAM
and explore an example plugin that you can experiment with.

For more in-depth documentation for developing plugins from scratch,
see:

* [GUIPlugin documentation](gui-plugin.md)
* [OperationPlugin documentation](operation-plugin.md)
* [Workflow documentation](workflow.md)

## Install Xi-CAM

If you haven't already installed Xi-CAM, follow the installation
instructions for your operating system:

* [Linux Installation](install-linux.md)
* [macOS Installation](install-macos.md)
* [Windows Installation](install-windows.md)

## Overview

In this guide we will:

* Explore the main window of Xi-CAM
* Download and install an Example Plugin
* Configure a sample catalog so we can load data
* Explore the Example Plugin

## Loking at Xi-CAM's Main Window

Let's look at what the main window in Xi-CAM looks like first:

```eval_rst
.. figure:: _static/xicam-main.png
  :alt: Xi-CAM main window after loading.

  The main window of Xi-CAM after it has finished loading.
```

When Xi-CAM finishes loading, we see the window as shown above.
Any installed plugins will be visible (and selectable) at the top
(note that you will probably not have any installed yet).

We can also see some of the default widgets provided:
* a welcome widget in the *center* of the window
* a preview widget in the top-left (*lefttop*) of the window,
which shows a sample of selected data in the data browser widget
* a data browser widget on the *left* of the window,
which can show available databroker catalogs

### Quick GUILayout Overview

We mentioned the terms *center*, *lefttop*, and *left* above.
These correspond to a `GUILayout`,
which can be thought of as a 3 row by 3 column layout.

Here is a *quick* overview of how the Xi-CAM main window is organized:

```eval_rst
.. figure:: _static/xicam-layout.png
  :alt: Layout of Xi-CAM's main window

  The layout of Xi-CAM's main window.
```

You can see that the layout of Xi-CAM follows a 3x3 grid,
where each section is named according to its orientation in relation to the center
of the window.

(Note that any `GUIPlugins` you create will have one or more of these `GUILayouts`).

### Xi-CAM Menu Bar

At the top of the main window,
there is a menu bar that contains some helpful items.

In the `File` item you can find `Settings` for Xi-CAM.
This includes things like:

* Logging configuration - where to find the log files, what type of logging record...
* Theme - change the appearance of Xi-CAM
* ...

In the `Help` item you can find a link to the Xi-CAM documentation,
a way to contact the development team,
and versioning / licensing information for Xi-CAM.

## Download and Install the ExamplePlugin

Now that we have looked at the main window and its layout,
let's download the Example Plugin.

```bash
cd ~
git clone https://github.com/Xi-CAM/Xi-CAM.ExamplePlugin
cd Xi-CAM.ExamplePlugin
```

### What's Inside the ExamplePlugin Repository

The repository will contain the following:

```eval_rst
.. figure:: _static/xicam-example-plugin-dirs.png
  :alt: Contents of ExamplePlugin repo

  The contents of the ExamplePlugin repo when you clone it.
```

At the top there are a few files and directories:

* `setup.py` - describes how to install this as a python package;
**also used to register plugins (via entry points)**.
* `configure` - special directory for this example, helps set up a catalog
* `xicam` - directory that acts as a python namespace package

In `xicam`, there is a `exampleplugin` subpackage that contains:

* `__init__.py` - makes `exampleplugin` a python package; also exposes the `ExamplePlugin` class
* `exampleplugin.py` - module that contains the `ExamplePlugin` GUI plugin
* `operations.py` - module that contains the example `OperationPlugins`
* `workflows.py` - module that contains the example `Workflows`

### How Do I Install the Example Plugin?

So far, we have only downloaded the Example Plugin -
we still need to install it so Xi-CAM can find it and load it.

We can install downloaded plugins using a *pip editable install*:

```bash
pip install -e .
```

#### Entry Points

If you are interested in how this works,
here's a short summary of how the Example Plugin defines entry points
so Xi-CAM can find the plugins here.
(There is more information in the documentation;
for purposes of this quick start guide, we won't go into too much detail.)

There are some entry points defined in the `setup.py` file
that will tell Xi-CAM what plugins it can find:

```python
entry_points={
    'xicam.plugins.GUIPlugin':
        ['example_plugin = xicam.exampleplugin:ExamplePlugin'],
    'xicam.plugins.OperationPlugin':
        [
            'invert_operation = xicam.exampleplugin.operations:invert',
            'random_noise_operation = xicam.exampleplugin.operations:random_noise'
        ]
    }
```

In short, Xi-CAM will see the `xicam.plugins.GUIPlugin` entry point key 
and load in the `ExamplePlugin` defined (in the value).
Similarly, Xi-CAM will see the `xicam.plugins.Operation` entry point key
and load in `invert` and `random_noise` operations.

### Run Xi-CAM

When you run `xicam`, 
you should now see the Example Plugin available at the top right of the main window.

### Setting up the Example Catalog

Now that we have the Example Plugin installed,

## Exploring the Example Plugin

---
## Xi-CAM Main Window

Let's look at what the main window looks like first:

```eval_rst
.. figure:: _static/xicam-main.png
  :alt: Xi-CAM main window after loading.

  The main window of Xi-CAM after it has finished loading.
```

When Xi-CAM finishes loading, we see the window as shown above.
Any installed plugins will be visible (and selectable) at the top
(note that you will probably not have any installed yet).

We can also see some of the default widgets provided:
* a welcome widget in the *center* of the window
* a preview widget in the top-left (*lefttop*) of the window
* a data browser widget on the *left* of the window

When creating our GUIPlugin, we will provide our own *center* widget,
but we will not be modifying the *lefttop* or the *left* widgets.

## GUIPlugin

Now that we have a basic overview of the Xi-CAM main window,
we need to create and install a GUIPlugin for Xi-CAM.

A GUIPlugin is the user-facing plugin that you will see when loading Xi-CAM
(they will show up in the top area of the main window).

### Clone the ExamplePlugin Repository

For purposes of this quick-start tutorial,
we will create a GUIPlugin named "Example Plugin".

Go ahead and open a terminal (or if on Windows, you can use your Anaconda prompt)
and make sure that your xicam environment that you created is active.

`cd` to a directory of your choice (like your home directory),
then get the starting code:

```bash
git clone https://github.com/Xi-CAM/Xi-CAM.ExamplePlugin
cd Xi-CAM.ExamplePlugin
```

### Install the ExamplePlugin

Now that we have downloaded the starting code for our `ExamplePlugin`,
we need to actually *install* the plugin so Xi-CAM can see it.

To do this, we use what's called an *editable pip install*.
Ensuring that you are in the `Xi-CAM.ExamplePlugin` directory, run:

```bash
pip install -e .
```

Next, run xicam:

```bash
xicam
```

You should now have "Example Plugin" appear at the top of your Xi-CAM window.

### Exploring the ExamplePlugin

Go ahead and click on the "Example Plugin" text;
this will select and activate the `ExamplePlugin` GUIPlugin.

```eval_rst
.. figure:: _static/xicam-example-plugin.png
  :alt: Interface for the Example Plugin

  The interface for the "Example Plugin".
```

Notice that the top has the "Example Plugin" selected.
All this GUIPlugin contains right now is the text "Stage 1..." in the center of the window.

### Modifying the ExamplePlugin

Let's make some modifications to the `ExamplePlugin` so it can load an image from a local databroker.

Go ahead and close Xi-CAM.

#### Configuring the Sample Databroker Catalog

First, we will need to configure a catalog called "example-catalog" for Xi-CAM to find with databroker.

There should be a `configure/` directory in the repository we cloned.
This contains a catalog configuration file, a msgpack catalog, and a script.

Feel free to inspect the script before you run it;
it will attempt to set up a msgpack catalog source for Xi-CAM to use:

```bash
cd configure
python setup_catalog.py
cd ..
```

##### Data Resource Browser

Now that we've configured the catalog,
let's make sure that Xi-CAM can see it.

Look at the *Data Resource Browser* on the left hand side of the window.
After configuring our example catalog,
it should have the text "example-catalog" in the *Catalog* drop-down box.

Notice that it also has two text inputs, *Since* and *Until*.
Our example catalog was created in the beginning of 2020.
In order to see the data (catalogs) our "example-catalog" contains,
we need to change the *Since* text input.

Change it's value to "2020-01-01".
This will now look for any data that was created since the start of 2020.
After making this change,
the example-catalog will be re-queried for data created within these new dates.

You should see a catalog show up in the table below with the id *349497da*.
If you *single-click* the row in the table to highlight it,
more information and a preview of the data should be shown as well:

```eval_rst
.. figure:: _static/xicam-example-catalog.png
  :alt: Our example-catalog showing a catalog and preview.

  Here we see catalog 349497da.
  It has one stream (primary) with 10 events in it.
  A preview shows the first frame of the data,
  which is a picture of Clyde the cat.
```

#### Trying to Load the Catalog

Let's see what happens if we try to load the catalog.

Try load the 349497da catalog by either
double-clicking it or selecting it and clicking the "Open" button.

You will get an error asking you to select a GUIPlugin before loading a catalog.
This is an important point to remember:

**When loading a catalog into Xi-CAM,
you must have a GUIPlugin active.**

So, go ahead and select the "Example Plugin".
If you try to open the catalog now,
you still will not see anything loaded into the "Example Plugin".

This is the second point to remember when trying to load catalogs:

**In order to load a catalog into your GUIPlugin,
you must implement the `appendCatalog` method in your GUIPlugin.**

#### Implementing appendCatalog

Let's implement the `appendCatalog` method in `ExamplePlugin`
so we can load the catalog.
We will also be adding a widget to view the loaded catalog.

Inside of the `ExamplePlugin` class,
add the `appendCatalog` as follows:

```python
from qtpy.QtWidgets import QLabel

from xicam.core.msg import logMessage
from xicam.plugins import GUILayout, GUIPlugin
from xicam.gui.widgets.imageviewmixins import CatalogView


class ExamplePlugin(GUIPlugin):
    # Define the name of the plugin (how it is displayed in Xi-CAM)
    name = "Example Plugin"

    def __init__(self, *args, **kwargs):
        self._catalog_viewer = CatalogView()
        self._stream = "primary"
        self._field = "img"

        catalog_viewer_layout = GUILayout(self._catalog_viewer)
                
        # Modify stages here
        # self.stages = {"Stage 1": GUILayout(QLabel("Stage 1..."))}
        self.stages = {"View Catalog": catalog_viewer_layout}

        super(ExamplePlugin, self).__init__(*args, **kwargs)

    def appendCatalog(self, catalog):
        self._catalog_viewer.setCatalog(catalog, self._stream, self._field)
        logMessage(f"Opening catalog with stream {self._stream} and field {self._field}.")
        

```

#### Changing the Layout



## OperationPlugin

Now that we have our GUIPlugin created and installed in Xi-CAM,
we can start creating our operations.

An operation can be thought of as a function; input data is sent into the operation,
and the operation generates some output with the given input.

The OperationPlugin API makes use of python decorators for easily defining
and creating operations.

In the 

## Workflow


####NOTES TO SELF
* Write a demo repo for this, with good commits
* Quickstarting can be exploring the completed demo
* Need to provide catalog example data, catalog file, how to do...

* Move the details about implementing the Example Plugin into GUIPlugin
