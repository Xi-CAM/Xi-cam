# PyCharm

Pycharm is one of many integrated development environments (IDEs).
These provide useful tools for writing and running code.
We recommend installing PyCharm to help with writing Xi-CAM operations and plugins.

## Installation

You can download and install the Pycharm Community (Free) Edition here:
https://www.jetbrains.com/pycharm/download/

## Configuring PyCharm for Xi-CAM

After installing, we need to set up PyCharm for writing operations and running Xi-CAM.

### Creating a project

First, we will need to create a project for the code you will be writing.
This will select a directory for writing code and activate your `xicam` environment.

Create a new project: `File -> New Project...`.
This will show the `Create Project` dialog.

In the `Location` line, click on the folder icon to browse to the `Xi-CAM Plugins` folder in your HOME area.
(Create this folder if it doesn't already exist under your home).
This is where we will be writing our code.

In the `Python Intepreter` section, select the `Previously configured interpreter` option.
Then, click the `...` on the right to open the `Add Python Intepreter` dialog.
Select `Conda Environment` on the left.
Click on the `Interpreter` drop-down to select the `xicam` environment.
Click `OK`.

Uncheck `Create a main.py welcome script`, then click `Create`.

#### Running Xi-CAM in PyCharm

In order to run Xi-CAM in PyCharm, you need to add a run configuration.

To do this, navigate the menu as follows: `Run -> Edit Configurations...`.

In the `Script Path` line, click on the folder icon and browse to the `xicam` executable.

To see where Xi-CAM was installed, see the following to determine the paths to the xicam executable:

* Windows: In Anaconda Prompt with xicam env active, run `%CONDA_PREFIX%\bin\xicam`.
* macOS/Linux: In terminal with xicam env active, run `echo $CONDA_PREFIX/bin/xicam`.

Ensure that the `Python Interpreter` is set to your `xicam` environment.

Click `OK`.


## Helpful PyCharm Tips

You can navigate in the menu as follows: `Help -> IDE Features Trainer`,
which is an interactive lesson plan for learning the IDE.