import pathlib

import virtualenv
from appdirs import user_config_dir, site_config_dir

user_venv_dir = user_config_dir('xicam/venvs')
site_venv_dir = site_config_dir('xicam/venvs')

venvs = {}
observers = []

# Python 2 style execfile function
execfile = lambda filename, globals=None, locals=None: exec(open(filename).read(), globals, locals)


def create_environment(name: str):
    """
    Create a new virtual environment in the user_venv_dir with name name.

    Parameters
    ----------
    name : str
        Name of virtual envirnoment to create.
    """
    virtualenv.create_environment(str(pathlib.Path(user_venv_dir, name)), site_packages=False, clear=False,
                                  unzip_setuptools=False,
                                  prompt=None, search_dirs=None, download=False,
                                  no_setuptools=False, no_pip=False, no_wheel=False,
                                  symlink=True)


def use_environment(name):
    """
    Activate the virtual environment with name name in user_venv_dir

    Parameters
    ----------
    name : str
        Name of virtual environment to activate
    """

    activate_script=pathlib.Path(user_venv_dir, name, "bin", "activate_this.py")
    if not activate_script.is_file():
        activate_script = pathlib.Path(user_venv_dir, name, "Scripts", "activate_this.py")
    if not activate_script.is_file():
        raise ValueError(f"Virtual environment '{name}' could not be found.")

    activate_script = str(activate_script)
    execfile(activate_script, dict(__file__=activate_script))
    for observer in observers:
        observer.venvChanged()


# TODO: create default environment if it doesn't exist
# TODO: find all venvs; populate the venvs global
# create_environment("default")
use_environment("default")
current_environment = str(pathlib.Path(user_venv_dir, "default"))
