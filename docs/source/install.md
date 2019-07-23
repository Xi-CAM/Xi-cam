# Installing Xi-cam

Installing Xi-cam for developing plugins requires some system configuration.
By following this guide, you will have Xi-cam running and ready for
development.

## Install git and python3

You will need to ensure that you have both **git** and **python3** installed on
your system for Xi-cam development. You will also probably want to install
a text editor or IDE (integrated development environment) for writing python 
code. For a python IDE, we recommend
[PyCharm Community Edition](https://www.jetbrains.com/pycharm/download/).

### macOS

Open the **Terminal** application (in Applications/Utilities). In the terminal,
check to see if git is installed by typing ```git --version```.
Either a version number will be printed, indicating git is already installed,
or a dialog will open asking **The "git" command requires the command line 
developer tools. Would you like to install the tools now?** Click the 
**Install** button to install the developer tools, which will install git for 
you.

You will also need to install python3. You can download python3 at
[python.org](https://www.python.org/downloads/release/python-373/). You will
want to get the **macOS 64-bit installer** if you are running any macOS version
since Mavericks.

### Windows

Download git [here](https://git-scm.com/download/win) and follow the installer's
instructions. This will install **Git for Windows**, which provides a **Git Bash**
command line interface as well as a **Git GUI** graphical interface for git.

You will want to go to the python3 download page at
[python.org](https://www.python.org/downloads/release/python-373/).
For modern systems, install the **Windows x86-64 executable installer** at
the bottom. 

When you run the installer, make sure sure to check the box that says 
**Add Python 3.x to PATH** to ensure that the interpreter will be placed in your
execution path.

## Create and Activate a Virtual Environment

The latest python3 version comes with the **venv** module, which can be used
to create a virtual environment. A virtual environment is a sequestered space
where you can install and uninstall packages without modifying your system's
installed packages.

Create a virtual environment for installing the Xi-cam components and 
dependencies. You will then want to activate the virtual environment you
created so that any packages you install with python's package manager, **pip**,
will be installed into that active virtual environment. In the commands below,
create a virtual environment called **venv** and activate it:

### macOS

```
python3 -m venv venv
source venv/bin/actviate
```

### Windows

```
python -m venv venv
venv\Scripts\activate
```

## Install Xi-cam and Core Dependencies

Xi-cam depends on a GUI library package called Qt; you will need to install
one of the python bindings for Qt in order to install Xi-cam.
You can install the **PyQt5** pip package as follows:

```
pip install PyQt5
```

Clone the primary Xi-cam repositories needed for development: Xi-cam.core,
Xi-cam.gui, Xi-cam.plugins, and Xi-cam.

Then, install these into your active virtual environment via pip.
Use the **-e** option to create an editable installation. This allows you to
modify any code in these repos and see the changes without having to run
`pip install` again. (If on Windows, run the following commands using
**Git Bash**.)

```
git clone https://github.com/lbl-camera/Xi-cam.core
cd Xi-cam.core 
pip install -e .
cd ..

git clone https://github.com/lbl-camera/Xi-cam.plugins
cd Xi-cam.plugins
pip install -e .
cd ..

git clone https://github.com/lbl-camera/Xi-cam.gui
cd Xi-cam.gui
pip install -e .
cd ..

git clone https://github.com/lbl-camera/Xi-cam
cd Xi-cam
pip install -e .
```

To ensure everything is installed correctly, you can run Xi-cam. In the
**Xi-cam** directory, run:

```
xicam
```

<!--
NOTES
-----
Anaconda to keep PATH active (opposed to having to activate every time)

-->

<!--
* test these instructions on windows
    * test the install
    * test the venv creation
    * test the cloning (git bash?)
    * test run_xicam
-->
