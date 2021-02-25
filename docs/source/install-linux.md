# Installing Xi-CAM for Linux

Installing Xi-CAM requires a few system components to be installed.
After successfully installing these components and Xi-CAM,
you will be ready to start developing Xi-CAM plugins!

## Supported python versions

* python3.8
* python3.7

## Create and Activate a Virtual Environment

Creating a virtual environment allows you to install and uninstall packages
without modifying any packages on your system. This is *highly* recommended.

There are a couple of ways to create a virtual environment:

1. via **conda** tool (_provides python3 for you;_ provided by anaconda.org or miniconda.org)
1. via the **venv** module provided with python3

In the commands below, we will create a new environment called **xicam**
and then activate the environment. 

Once an environment is activated, any packages installed through pip will be installed into this
sequestered xicam environment. *(If using conda, you can install either with pip or conda.)*

### conda

If you would like to create an environment through conda,
you will first need to install conda from one of the following:

* [Anaconda](https://www.anaconda.com/products/individual#Downloads) - comes with an assortment of common python3 packages
* [Miniconda](https://docs.conda.io/en/latest/miniconda.html) - minimal installation of python3 and conda, no extra packages

Then, run the following:

```
cd ~
conda create -n xicam python=3.8
conda activate xicam
```

(Note that you can see where your active environment is located by running```echo $CONDA_PREFIX```.)

### virtualenv

If you would like to create a virtual environment,
you will first need to ensure you have python3 installed on your system.
You can check this with ```python --version``` or ```python3 --version```.
If not installed, consult your specific distribution's package manager for installing python3.

Then, run the following:

```
cd ~
python3 -m venv xicam
source xicam/bin/actviate
```

## Install the Xi-CAM package

Now that we have activated a new **xicam** environment,
we can install Xi-CAM:

```
pip install xicam
```

To ensure everything is installed correctly, you can run Xi-CAM as follows:

```
xicam
```

## Where Do I Go from Here?

You are now ready to start developing plugins for Xi-CAM!

To learn about developing plugins for Xi-CAM, see the [Quick Start Guide](quickstart.md).