# Installing Xi-CAM for Windows

Guide for installing Xi-CAM for March 2, 2021 Xi-CAM Hackathon.
Copyable commands shown at bottom of document.

## Create and Activate a Conda Environment

On Windows, a great way to manage python installations and packages is through Anaconda.
Download the [Anaconda (Python3.8) installer](https://www.anaconda.com/products/individual#Downloads)
and follow the [Windows installation instructions](https://docs.anaconda.com/anaconda/install/windows/),
which will install the conda package manager, Anaconda, Anaconda Prompt, and Anaconda Navigator.

* Anaconda -- A package that provides conda and several common python packages
* Anaconda Prompt -- A command line shell for managing conda environments and installing packages
* Anaconda Navigator -- A GUI for managing conda environments and installing packages

Open the Anaconda Prompt program.

Then, we will create a new environment called **xicam**.
This creates a sequestered space on your system to install xicam and its dependencies
without modifying any of your system's libraries.

Next, we will activate the environment.
This tells the system to use the libraries and applications inside the environment.

```bash
conda create -n xicam
conda activate xicam
```

## Install the latest version of Xi-CAM

Now that we have activated a new **xicam** environment,
we can install the latest development version of Xi-CAM,
directly from GitHub.
Run the following in Anaconda Prompt:

```
pip install git+https://github.com/Xi-CAM/Xi-cam.git
```

To verify the installation was successful, you can run Xi-CAM as follows:

```
xicam
```

## Copyable Instructions

Anaconda Prompt:

```bash
cd ~
conda create -n xicam
conda activate xicam

pip install git+https://github.com/Xi-CAM/Xi-cam.git

xicam
```
