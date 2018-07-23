import pathlib

import sys, os
import venv
from appdirs import user_config_dir, site_config_dir, user_cache_dir
import subprocess
import platform

op_sys = platform.system()
if op_sys == 'Darwin':  # User config dir incompatible with venv on darwin (space in path name conflicts)
    user_venv_dir = os.path.join(user_cache_dir(appname='xicam'),'venvs')
else:
    user_venv_dir = os.path.join(user_config_dir(appname='xicam'),'venvs')
site_venv_dir = os.path.join(site_config_dir(appname='xicam'),'venvs')

venvs = {}
observers = []

# Python 2 style execfile function
execfile = lambda filename, globals=None, locals=None: exec(open(filename).read(), globals, locals)

# TODO: transition to http://virtualenvwrapper.readthedocs.io/en/latest/index.html


def create_environment(name: str):
    """
    Create a new sandbox environment in the user_venv_dir with name name.

    Parameters
    ----------
    name : str
        Name of sandbox environment to create.
    """

    envpath = pathlib.Path(user_venv_dir, name)
    if envpath.is_dir():
        return
        # raise ValueError('Environment already exists.')
    venv.create(envpath, with_pip=True)


def use_environment(name):
    """
    Activate the sandbox environment with name name in user_venv_dir

    Parameters
    ----------
    name : str
        Name of sandbox environment to activate
    """
    path = pathlib.Path(user_venv_dir, name)
    if not path.is_dir():
        raise ValueError(f"Sandbox environment '{name}' could not be found.")

    global current_environment
    current_environment = str(path)
    activate_this(current_environment)

    for observer in observers:
        observer.venvChanged()


def activate_this(path):
    # Below copied and modified from the activate_this.py module of virtualenv, which is missing form venv
    old_os_path = os.environ.get('PATH', '')
    os.environ['PATH'] = os.path.dirname(os.path.abspath(path)) + os.pathsep + old_os_path
    base = os.path.dirname(os.path.dirname(os.path.abspath(path)))
    if sys.platform == 'win32':
        site_packages = os.path.join(base, 'Lib', 'site-packages')
    else:
        site_packages = os.path.join(base, 'lib', 'python%s' % sys.version[:3], 'site-packages')
    prev_sys_path = list(sys.path)
    if not getattr(sys, 'frozen', False):  # site missing addsitedir when frozen
        import site
        site.addsitedir(site_packages)

    sys.real_prefix = sys.prefix
    sys.prefix = base
    # Move the added items to the front of the path:
    new_sys_path = []
    for item in list(sys.path):
        if item not in prev_sys_path:
            new_sys_path.append(item)
            sys.path.remove(item)
    sys.path[:0] = new_sys_path


# TODO: find all venvs; populate the venvs global
create_environment("default")
use_environment("default")
current_environment = str(pathlib.Path(user_venv_dir, "default"))
