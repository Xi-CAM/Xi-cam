import pathlib

import sys, os
import virtualenv
from appdirs import user_config_dir, site_config_dir, user_cache_dir
import subprocess
import platform

op_sys = platform.system()
if op_sys == 'Darwin':  # User config dir incompatible with venv on darwin (space in path name conflicts)
    user_venv_dir = user_cache_dir('xicam/venvs')
else:
    user_venv_dir = user_config_dir('xicam/venvs')
site_venv_dir = site_config_dir('xicam/venvs')

venvs = {}
observers = []

# Python 2 style execfile function
execfile = lambda filename, globals=None, locals=None: exec(open(filename).read(), globals, locals)

# TODO: transition to http://virtualenvwrapper.readthedocs.io/en/latest/index.html


def create_environment(name: str):
    """
    Create a new virtual environment in the user_venv_dir with name name.

    Parameters
    ----------
    name : str
        Name of virtual envirnoment to create.
    """
    venvpath = str(pathlib.Path(user_venv_dir, name))

    if not os.path.isdir(venvpath):
        env = os.environ.copy()
        if not 'python' in os.path.basename(sys.executable):
            python = os.path.join(os.path.dirname(sys.executable), 'python')
            env['VIRTUALENV_INTERPRETER_RUNNING'] = 'true'
        else:
            python = sys.executable

        p = subprocess.Popen([python, virtualenv.__file__, venvpath], env=env)
        p.wait()



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
    global current_environment
    current_environment = str(pathlib.Path(user_venv_dir, name))
    for observer in observers:
        observer.venvChanged()


# TODO: create default environment if it doesn't exist
# TODO: find all venvs; populate the venvs global
create_environment("default")
os.sync()
use_environment("default")
current_environment = str(pathlib.Path(user_venv_dir, "default"))
