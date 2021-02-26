# Installing Xi-CAM for Linux

## Create and Activate a Conda Environment

Creating a virtual environment allows you to install and uninstall packages
without modifying any packages on your system.

We will install the **conda** tool, which provides python 3 for you.

In the commands below, we will create a new environment called **xicam**
and then activate the environment. 

Once an environment is activated, any packages installed through pip will be installed into this
sequestered xicam environment. *(If using conda, you can install either with pip or conda.)*

### conda

First, install conda from [Anaconda](https://www.anaconda.com/products/individual#Downloads)
(you'll want the Python3.8 version).

Then, run the following:

```
cd ~
conda create -n xicam
conda activate xicam
```

(Note that you can see where your active environment is located by running```echo $CONDA_PREFIX```.)

## Install the latest version of Xi-CAM

Now that we have activated a new **xicam** environment,
we can install the latest development version of Xi-CAM,
directly from GitHub:

```
pip install git+https://github.com/Xi-CAM/Xi-cam.git
```

To verify the installation was successful, you can run Xi-CAM as follows:

```
xicam
```
