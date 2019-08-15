# Creating a GUIPlugin

Xi-cam provides the GUIPlugin class for writing a Qt widget-based plugin.
By deriving a GUIPlugin, you can define a custom plugin in Xi-cam that can
be used to load, process, and analyze data.

See the
[Resources](resources.md) page for more information about Qt and QtPy.

## Prerequisites

If you have not installed Xi-cam for development, follow the instructions on the 
[Installing Xi-cam](install.md) page.

Also, *make sure that your xicam virtual environment (venv) is activated*. 

For Windows, commands will be run with
Git Bash. For macOS and Linux, commands will be run on the terminal.

## Core Concepts

The core concepts to keep in mind when creating a GUIPlugin are stages, GUI layouts, data handlers, and
workflows. We will start with stages and GUI Layouts since they are closely tied to each other.

### Stages

Stages are used to organize user work flow in a GUIPlugin.
Each stage represents a collection of widgets used to perform some task. 
A GUIPlugin must have at least one stage.

Stages are defined as as an ordered dictionary,
where each key represents a stage's name and each associated value
is a [GUILayout](#gui-layouts) that defines the organization of widgets for that stage.
The key will be used at the stage's display name in Xi-cam.

As an example, we could have a Demo GUIPlugin that has the stages
X and Y. To set these stages, we would set the
GUIPlugin's stages property:

```python
self.stages = {
    'X': GUILayout(xWidget),
    'Y': GUILayout(yWidget)
}
```

This creates two stages, X and Y, in your GUIPlugin.
When clicking the Demo plugin on the top of the main window, you would see:

> Demo | X | Y | &uarr;


[//]: <> (For example, if we
have a GUIPlugin called MovieEnhance, we could break apart its user work flow
into separate but related components. MovieEnhance could be broken down into
a user workflow where the user can view the raw images and select a
region-of-interest, "enhance" the region-of-interest, then crop for a final
enhanced product image. These steps can be represented by stages: Examine,
Enhance, Crop.)

### GUI Layouts

The GUILayout class represents a layout of widgets to use in a GUIPlugin stage.
The main window in Xi-cam is organized in a 3 x 3 grid. 
These cells in the grid are named according to their positions in the grid: 
center, top, bottom, left, lefttop, leftbottom, right, righttop, rightbottom. 

When creating a GUILayout, a *center* widget must be provided; 
the other positions are optional. 
Also note that the *lefttop* and *left* widgets are already occupied 
by the main window's preview widget
and data resource browser (i.e. file browser), respectively.
Although it is possible to provide your own *left* and *lefttop* widgets,
it is not recommended as it will replace those main window widgets.

### Data Handlers

If your plugin needs to load data and/or store internally processed data, the plugin will need a way to ingest
the data into Xi-cam and then store data internally.

### DataHandlerPlugin

The DataHandlerPlugin class provides a mechanism to ingest data into Xi-cam. If you have a custom data format or the
data you want to load is not currently a format Xi-cam can load, you will need to implement your own
DataHandlerPlugin.
 
See [Creating a DataHandlerPlugin](data-handler.md) for more information.

### GUIPlugin header methods

Once data is ingested into Xi-cam, you will need a uniform way to access this internal data.
The GUIPlugin class provides an interface for storing and accessing this data. You will need to override
(i.e. implement your own version of) a few GUIPlugin methods in your own derived GUIPlugin class:

**appendHeader** is *intended* to be used to internalize data in your derived GUIPlugin. You *must* override this
method if you want to add ingested data (`NonDBHeader`) to your internal data model (`QStandardItemModel`).

**currentheader** is *intended* to be used to retrieve the current (active, focused, etc.) internalized data. You
*must* override this method if you intend to use it. 

**headers** is used to get a list of all of the data items in the data model. *This method expects that a `headermodel`
attribute be created in your GUIPlugin class. This attribute is usually some type of Qt model 
(e.g. `QStandardItemModel`) (the `headermodel` attribute is expected to be a type that implements
`item()` and `rowCount()` methods).*

### Workflows

In Xi-cam a `Workflow` represents a way to organize a set of processes (with inputs and outputs) and execute these 
processes. Here, a process is a `ProcessingPlugin`. You will want to create a Workflow when you want to parameterize
and perform processes (i.e. operations) on your data.

For more information, see the [Workflow](workflow.md) documentation.

---

## Creating your First GUIPlugin

After reviewing the core concepts, we can start implementing our own GUIPlugin.
We will create a simple GUIPlugin that allows viewing loaded images, then we
will extend that plugin with more features until we have a MovieEnhance plugin.

When first starting to write Xi-cam GUIPlugins, it is recommended to use a `cookiecutter`
template to set up some basic code and infrastructure for you.

### Using cookiecutter to Create the Plugin
[cookiecutter](https://cookiecutter.readthedocs.io/en/latest/readme.html) is a tool for creating
python projects from a template file.

There is a Xi-cam GUIPlugin template for cookiecutter that helps set up some packaging infrastructure
and boiler-plate code for a GUIPlugin. Follow the instructions here:
[Xi-cam.templates.GuiPlugin repo](https://github.com/synchrotrons/Xi-cam.templates.GuiPlugin).

When cookiecutter is run with the GUIPlugin template file, it will prompt for some information
that is used to create the package. Most of the prompts will have default values, indicated
as `[somevalue]` next to the prompt.

Here are the prompts with descriptions and values that we will use:

prompt | description | our value
--- | --- | ---
package_name     | name of the plugin package (also the name displayed in Xi-cam)     | mydemo
display_name     | name of plugin (shows up in docs and README)                       | My Demo Plugin
plugin_version   | current plugin version number                                      |
plugin_file_name | file to put the generated plugin code into                         |
author_name      | name of the plugin's author                                        | &lt; Your Name &gt;
author_email     | author's email                                                     | &lt; Your Email &gt;
author_url       | url for the author/plugin (this is used as the plugin repo url)    | &lt; Your Plugin Repo &gt;
description      | description of the plugin                                          | Demonstrates a simple GUIPlugin
keywords         | keywords to tag the plugin with                                    |
dependencies     | packages the plugin depends on                                     | 
plugin_code      | additional code to put in the plugin implementation file           |
stages_code      | python dictionary to set the plugin's stages to                    |
yapsy_ext        | file extension of the plugin marker file                           |

This generates the following in your current directory:

```
Xi-cam.plugins.mydemo/
  docs/
    ...
  LICENSE.md
  MANIFEST.in
  README.md
  requirements.txt
  setup.cfg
  setup.py
  tests/
    ...
  update_docs.sh
  xicam/
    mydemo/
      __init__.py
      mydemo.yapsy-plugin
```

The plugin code will be located in *Xi-cam.plugins.mydemo/xicam/mydemo/__init__.py, which should look like:

```python
from qtpy.QtCore import *
from qtpy.QtGui import *
from qtpy.QtWidgets import *
from qtpy import uic
import pyqtgraph as pg

from xicam.core import msg
from xicam.plugins import GUIPlugin, GUILayout

class mydemo(GUIPlugin):
    name = 'mydemo'

    # insert GUI plugin generation


    def __init__(self, *args, **kwargs):
        # insert auto generation
        self.stages = {'Stage 1': GUILayout(QLabel('Stage 1'))}
        super(mydemo, self).__init__(*args,**kwargs)
```

#### Setting up VCS (Version Control System)

*If you are familiar with VCS and git, continue to the next section.*

You will need to initialize the directory cookiecutter created, `Xi-cam.plugins.mydemo`, 
as a repository:

```
cd Xi-cam.plugins.mydemo
git init .
```

You will then want to add a .gitignore file to tell what files git shouldn't look at.
You can copy the .gitignore from the Xi-cam repository you cloned during installation.

The repository is initialized, but we still need to tell git what files we want to add. To do this, we can add all of
the non-ignored files by running `git add .`.

This *stages* the changes, meaning that git will save these to your local repository once you commit those changes.
To save these changes, run `git commit -m "Create mydemo plugin from cookiecutter template`. Now these changes are
saved locally.

You will want to then set up your remote (e.g. GitHub). If you want to push your code up to GitHub, you will first want
to [create a new GitHub repository](https://help.github.com/en/articles/creating-a-new-repository). *Do not initialize
this repository with a README, .gitignore, or license (by default these will not be created).*

GitHub will then give you some instructions with how to add files to the new repository. You will want to follow the
steps under *push an existing repository from the command line* (it will show a `git remote` command and a
`git push` command).

#### Installing the plugin

After creating the plugin, we need to tell Xi-cam that it is available to use. One way to do this is to create an
editable pip install. Make sure you are in your plugin's directory (Xi-cam.plugins.mydemo), then run:

```
pip install -e .
```

This will allow Xi-cam to see your plugin and load it.

#### Verifying

Run xicam to verify that your plugin loads properly.
At the top-right of the Xi-cam main window, you should see *mydemo*.
When you click it, you should see the text *Stage 1* in the middle of the main window.

---

## Extending your GUIPlugin

After verifying that your plugin is loading in Xi-cam, we can begin to extend the GUIPlugin with custom
functionality.

### Example 1 - A Cropping Plugin

This example illustrates a simple GUIPlugin that can invert the values of an input image array.
Here, *invert* will mean taking the difference between the max integer value and the image pixel values.
For example, if we have an image that stores 8-bit unsigned data (values 0 to 255), we will subtract
the pixel value from 255.

First, we will need to create a ProcessingPlugin for our inversion process.
We can add an Invert class to our *mydemo* package(*Xi-cam.plugins.mydemo/xicam/mydemo/__init__.py*).

Our Invert ProcessingPlugin needs to read in input data and output inverted data.
We can define Inputs and an Output in our Invert class to handle those appropriately.
We will also want to give this plugin a name and implement the evaluate method,
which actually does the 'process' (the inversion).

```python
import numpy as np

from xicam.plugins import ProcessingPlugin, Input, Output


class Invert(ProcessingPlugin):
    name = 'Invert'

    data = Input(description='Image array data to invert', type=np.ndarray)
    inverted = Output(description='Inverted image data', type=np.ndarray)

    def evaluate(self):
        
        invertVal = np.iinfo(self.data.value.dtype).max
        self.inverted.value = invertVal - self.data.value
```

Now that we have our Invert ProcessingPlugin implemented, we can begin to modify our GUIPlugin to communicate with it.
Let's first think about what stages we might need and the layouts of these stages in our GUIPlugin.

To get a quick implementation up and running, we can have one stage for now. This stage will have an image viewer widget
as its center widget. We will also add a tool bar as the top widget. The tool bar will have a tool button that can run 
the invert process when clicked. To do this, we will add a QAction to the tool bar using `QToolBar.addAction`. 

When an action is added to the toolbar, it will be displayed as a clickable widget (button).
In our case, this button will show the text *Invert* (when adding an action,
there are multiple ways to parameterize what the created action will display).
Adding an action also sets up the the triggered signal to the method (called a slot in Qt)
that we pass to the `addAction` method.
This means whenever the *Invert* button is clicked, an internal method (slot) will be called.

In Qt, signals and slots allow widgets (or any Qt objects) to communicate with each other.
Slots can be connected to (listen for) a signal.
A *signal* is *emitted* from a widget, typically when the widget state changes in some way.
A signal can be emitted without any slots being connected to it.
When a slot is connected to a signal, the slot is executed anytime the connected signal is emitted.
*For more information about Qt signals and slots,
see the [Qt section](resources.md#qt) on the resources page.*

Let's look at the `QToolBar.addAction(text, receiver)` ([ref](https://pyside.github.io/docs/pyside/PySide/QtGui/QToolBar.html?highlight=qtoolbar#PySide.QtGui.PySide.QtGui.QToolBar.addAction)):
```
PySide.QtGui.QToolBar.addAction(text, receiver)

This is an overloaded function.

Creates a new action with the given text . This action is added to the end of the toolbar. 
The action’s PySide.QtGui.QAction.triggered() signal is connected to member in receiver .
```

We will need to provide text for the action that is created as well as the receiver (slot) method.
This method will be responsible for creating a Workflow, adding the InvertProcessPlugin to the Workflow,
executing the Workflow, then calling a method to grab the results of the Workflow (the inverted data)
and update the image.

For an input image, we will use on of Xi-cam's gui widgets, `DynImageView`, to display the image.
We will use numpy to generate our input image. We will create a 128x128 size image with each row
having values from 0 to 127.

The completed example (with added comments) looks like:

```python
from qtpy.QtCore import *
from qtpy.QtGui import *
from qtpy.QtWidgets import *
from qtpy import uic
import pyqtgraph as pg

import numpy as np

from xicam.core import msg
from xicam.core.execution import Workflow
from xicam.gui.widgets.dynimageview import DynImageView
from xicam.plugins import GUIPlugin, GUILayout, ProcessingPlugin, Input, Output


class Invert(ProcessingPlugin):
    # Define the plugin's name
    name = 'Invert'

    # Define inputs and outputs for the plugin
    data = Input(description='Image array data to invert', type=np.ndarray)
    inverted = Output(description='Inverted image data', type=np.ndarray)

    # This method does the 'processing'
    def evaluate(self):
        # Find the max possible value of the data stored in our image
        invertVal = np.iinfo(self.data.value.dtype).max
        # Invert
        self.inverted.value = invertVal - self.data.value


class mydemo(GUIPlugin):
    name = 'mydemo'

    # insert GUI plugin generation

    def __init__(self, *args, **kwargs):
        # Create tool bar
        self.toolBar = QToolBar()
        # When the 'Invert' action is triggered, call self.doInvertWorkflow
        self.toolBar.addAction('Invert', self.doInvertWorkflow)

        # Create an initial 8-bit 128x128 image
        self.imageViewer = DynImageView()
        imageData = np.empty(shape=(128, 128), dtype=np.uint8)
        imageData[:] = np.arange(imageData.shape[0])
        self.imageViewer.setImage(imageData)

        # Create the stages
        self.stages = {
            'Invert': GUILayout(self.imageViewer, top=self.toolBar)
        }

        super(mydemo, self).__init__(*args, **kwargs)

    def doInvertWorkflow(self):
        # Create a Workfow, add our Invert ProcessingPlugin to it
        workflow = Workflow()
        workflow.addProcess(Invert())
        # Pass the first ProcessingPlugin's Inputs here:
        # in our case, set the Invert ProcessingPlugin's 'data' Input.
        # When the processes are finished (just Invert in our case),
        # we can grab the results (Outputs) in the callback_slot.
        workflow.execute(data=self.imageViewer.image,
                         callback_slot=self.updateImageView)

    def updateImageView(self, results):
        # Our Workflow's results are ready, set our image to the inverted data
        self.imageViewer.setImage(results['inverted'].value)
```

[//]: <> (TODO:
DataHandler section
  is there a way to easily see registered data handlers? e.g. .hdf, .jpg, .bin, etc. are currently loadable
VCS section
  mention global git config?
  git ssh keys?
  add .gitignore to cookiecutter template .would be really useful, see Xi-cam's .gitignore for example file
Implementation section
  WorkflowEditor
  TabView
)



