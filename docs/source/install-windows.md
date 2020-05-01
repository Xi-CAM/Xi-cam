# Installing Xi-CAM for Windows

Installing Xi-CAM requires a few system components to be installed.
After successfully installing these components and Xi-CAM,
you will be ready to start developing Xi-CAM plugins!

## Install python3

On Windows, a great way to manage python installations and packages is through Anaconda.
Follow their [Windows installation instructions](https://docs.anaconda.com/anaconda/install/windows/),
which will install the conda package manager, Anaconda, Anaconda Prompt, and Anaconda Navigator.

* Anaconda -- A package that provides conda and several common python packages
* Anaconda Prompt -- A command line shell for managing conda environments and installing packages
* Anaconda Navigator -- A GUI for managing conda environments and installing packages

Open the Anaconda Prompt program.

Then, create a new environment called **xicam**.
This creates a sequestered space on your system to install xicam and its dependencies
without modifying any of your system's libraries.

Next, activate the environment.
This tells the system to use the libraries and applications inside the environment.

```bash
conda create -n xicam python=3.7
conda activate xicam
```

## Install Python Qt Bindings

Xi-CAM depends on a GUI application framework called Qt;
you will need to install
one of the python bindings for Qt (PyQt5 or PySide2) in order to run Xi-CAM.

*Make sure that you have activated the **xicam** environment.*

In your open Anaconda Prompt window, install the **pyqt** conda package as follows:

```bash
conda install pyqt
```

## Install the Xi-CAM package

Now that we have activated a new **xicam** environment and installed **pyqt**,
we can install Xi-CAM using a python package management tool called **pip**.
Run the following in your open Anaconda Prompt.

```bash
pip install xicam2
```

To ensure everything is installed correctly, you can run Xi-CAM as follows:

```bash
xicam
```

## Where Do I Go from Here?

You are now ready to start developing plugins for Xi-CAM!

You may wish to consult the [Resources Documentation](resources.md) as well for more information.

## Copyable Instructions

Anaconda Prompt:

```bash
cd ~
conda create -n xicam
conda activate xicam

conda install -c conda-forge pyqt

pip install xicam2

xicam
```