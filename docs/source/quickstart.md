# QuickStart Guide

This is a quick-start guide that will help you install Xi-CAM
and create a simple plugin inside of Xi-CAM.

## Install Xi-CAM

If you haven't already installed Xi-CAM, follow the installation
instructions for your operating system:

* [Linux Installation](install-linux.md)
* [macOS Installation](install-macos.md)
* [Windows Installation](install-windows.md)

## Overview

Let's dive into an example first that we can explore.

We will create a `GUIPlugin` - 
this will be a plugin that you will be able to select and see within Xi-CAM.
We can define the looks and feel of the `GUIPlugin` by using a `GUILayout`.

We will also create a few `OperationPlugins` - 
These plugins are basically functions that take in data
and output derived data.

After creating some `OperationPlugins`,
we will need a way to actually run data through the operations.
To do this, we will add these `OperationPlugins` into a `Workflow`.
Then, we will create a button in the GUI to execute the workflow.

Note that starting code for this guide can be found
[here](https://github.com/Xi-CAM/Xi-CAM.ExamplePlugin).

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
