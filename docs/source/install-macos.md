# Installing Xi-CAM for MacOS

Installing Xi-CAM requires a few system components to be installed.
After successfully installing these components and Xi-CAM,
you will be ready to start developing Xi-CAM plugins!

## Install python3

First, ensure that you have **python3** installed on your system.

The quickest way to do this is by downloading and running the python.org installer for python3.
The [python3.7.7 macOS 64-bit installer](https://www.python.org/downloads/release/python-377/)
works great here.

Alternatively, you can [install XCode and homebrew](https://docs.python-guide.org/starting/install3/osx/)
to manage multiple versions of python on your system.

## Create and Activate a Virtual Environment

Creating a virtual environment allows you to install and uninstall packages
without modifying any packages on your system. This is *highly* recommended.

There are a couple of ways to create a virtual environment:

1. via the **venv** module provided with python3
1. via **conda** (you will need to install this from anaconda.org or miniconda.org)

Using the **Terminal** application, we will create a new environment called **xicam**
in your home directory, and then activate the environment. 

Once an environment is activated, any packages installed through pip will be installed into this
sequestered xicam environment. *(If using conda, you can install either with pip or conda.)*

### virtualenv

```
cd ~
python3 -m venv xicam
source xicam/bin/actviate
```

### conda

```
cd ~
conda create -n xicam
conda activate xicam
```

## Install Python Qt Bindings

Xi-CAM depends on a GUI application framework called Qt;
you will need to install
one of the python bindings for Qt (PyQt5 or PySide2) in order to run Xi-CAM.

*Make sure that you have activated the **xicam** environment.*

For example, you can install the **PyQt5** pip package as follows:
```bash
pip install PyQt5
```

## Install the Xi-CAM package

Now that we have activated a new **xicam** environment and installed **PyQt5**,
we can install Xi-CAM:

```
pip install xicam2
```

To ensure everything is installed correctly, you can run Xi-CAM as follows:

```
xicam
```

## Where Do I Go from Here?

You are now ready to start developing plugins for Xi-CAM!

You may wish to consult the [Resources Documentation](resources.md) as well for more information.