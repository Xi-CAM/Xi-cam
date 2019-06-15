# Installing Xi-cam

## Install git, python3, and pip

You will need to ensure that you have both *git* and *python3* installed on
your system for Xi-cam development. You will also probably want to install
a text editor or IDE (integrated development environment) for writing python 
code.

`TODO -- need a section on what git is ?`

`TODO -- windows python either 64 or 32 bit`

### macOS

Open the **Terminal** application (in Applications/Utilities).
In the terminal, check to see if git is installed using ```git --version```.
Either a version number will be printed, indicating git is already installed,
or a dialog will open asking "The 'git' command requires the command line 
developer tools. Would you like to install the tools now?" Click the Install
button to install the developer tools, which will install git for you.


You will also need to install python3. You can download python3 at
[python.org](https://www.python.org/downloads/release/python-373/). You will
want to get the "macOS 64-bit installer" if you are running any macOS version
since Mavericks.

### Windows

Download git [here](https://git-scm.com/download/win) and follow the installer's
instructions. This will install **Git for Windows**, which provides a **Git Bash**
command line interface as well as a **Git GUI** graphical interface for git.

To install python3, you will first want to check if your system is 32-bit
or 64-bit architecture. To check this, search for **system information** and
click the **System Information** icon that shows up. If the search feature is not
enabled, open a file explorer window (either the folder icon on the bottom
of the screen or **WindowsKey + E**). On the left, you will need to right-click
**This PC**. Look for the **System type** text, which will tell you if you have
a 64-bit or 32-bit operating system.

Next, you will want go to the 
[python.org python3 download page](https://www.python.org/downloads/release/python-373/).
At the bottom, you will see **Windows x86-64 executable installer** and
**Windows x86 executable installer**. If you have a **32-bit** operating system,
download the **x86** installer. If you have a **64-bit** operating system,
download the **x86-64** installer.

### Install pip

`TODO -- what is pip`
pip can be installed on

`TODO -- Path configuration for windows python3 installer? check at home`

## Create and Activate Virtual Environment

Create a virtual environment and activate it so we can install the Xi-cam
components into a sequestered environment. This allows us to install 

```
python3 -m venv <directory>
source <directory>/bin/actviate
```

## Install Xi-cam and Core Dependencies

Clone the primary Xi-cam repositories needed for development: Xi-cam.core,
Xi-cam.gui, Xi-cam.plugins, and Xi-cam.

Then, install these into the virtual environment via pip. Use the **-e** option

```
git clone https://github.com/Xi-cam.core
cd Xi-cam.core 
pip install -e .
cd ..

git clone https://github.com/Xi-cam.gui
cd Xi-cam.gui
pip install -e .
cd ..

git clone https://github.com/Xi-cam.plugins
cd Xi-cam.plugins
pip install -e .
cd ..

git clone https://github.com/Xi-cam
cd Xi-cam
pip install -e .
python run_xicam.py
```