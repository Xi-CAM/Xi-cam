import platform
import os
import os.path
import sys
import venv

import pathlib
from appdirs import user_config_dir, site_config_dir, user_cache_dir
from qtpy.QtGui import QIcon
from qtpy.QtWidgets import QLabel

from xicam.gui.static import path
from xicam.plugins import SettingsPlugin

op_sys = platform.system()
if op_sys == "Darwin":  # User config dir incompatible with venv on darwin (space in path name conflicts)
    user_venv_dir = os.path.join(user_cache_dir(appname="xicam"), "venvs")
else:
    user_venv_dir = os.path.join(user_config_dir(appname="xicam"), "venvs")
site_venv_dir = os.path.join(site_config_dir(appname="xicam"), "venvs")

venvs = {}
observers = []

# Python 2 style execfile function
execfile = lambda filename, globals=None, locals=None: exec(open(filename).read(), globals, locals)


# TODO: transition to http://virtualenvwrapper.readthedocs.io/en/latest/index.html


class VenvsSettingsPlugin(SettingsPlugin):
    def __init__(self):
        if not current_environment:
            initialize_venv()

        self.widget = QLabel("test")
        super(VenvsSettingsPlugin, self).__init__(QIcon(str(path("icons/python.png"))), "Virtual Environments", self.widget)

    def toState(self):
        return None  # self.parameter.saveState()

    def fromState(self, state):
        pass  # self.parameter.restoreState(state)


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
    venv.EnvBuilder(with_pip=False).create(envpath)


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
    old_os_path = os.environ.get("PATH", "")
    os.environ["PATH"] = os.path.dirname(os.path.abspath(path)) + os.pathsep + old_os_path
    if sys.platform == "win32":
        site_packages = os.path.join(path, "Lib", "site-packages")
    else:
        site_packages = os.path.join(path, "lib", "python%s" % sys.version[:3], "site-packages")
    prev_sys_path = list(sys.path)
    # if not getattr(sys, 'frozen', False):  # site missing addsitedir when frozen
    try:
        import site

        addsitedir = site.addsitedir
    except AttributeError:  # frozen apps have no site-packages; and thus their site.py is fake
        # NOTE: relevant methods have been extracted from a real site.py
        def makepath(*paths):
            dir = os.path.join(*paths)
            try:
                dir = os.path.abspath(dir)
            except OSError:
                pass
            return dir, os.path.normcase(dir)

        def _init_pathinfo():
            """Return a set containing all existing file system items from sys.path."""
            d = set()
            for item in sys.path:
                try:
                    if os.path.exists(item):
                        _, itemcase = makepath(item)
                        d.add(itemcase)
                except TypeError:
                    continue
            return d

        def addpackage(sitedir, name, known_paths):
            """Process a .pth file within the site-packages directory:
               For each line in the file, either combine it with sitedir to a path
               and add that to known_paths, or execute it if it starts with 'import '.
            """
            if known_paths is None:
                known_paths = _init_pathinfo()
                reset = True
            else:
                reset = False
            fullname = os.path.join(sitedir, name)
            try:
                f = open(fullname, "r")
            except OSError:
                return
            with f:
                for n, line in enumerate(f):
                    if line.startswith("#"):
                        continue
                    try:
                        if line.startswith(("import ", "import\t")):
                            exec(line)
                            continue
                        line = line.rstrip()
                        dir, dircase = makepath(sitedir, line)
                        if not dircase in known_paths and os.path.exists(dir):
                            sys.path.append(dir)
                            known_paths.add(dircase)
                    except Exception:
                        print("Error processing line {:d} of {}:\n".format(n + 1, fullname), file=sys.stderr)
                        import traceback

                        for record in traceback.format_exception(*sys.exc_info()):
                            for line in record.splitlines():
                                print("  " + line, file=sys.stderr)
                        print("\nRemainder of file ignored", file=sys.stderr)
                        break
            if reset:
                known_paths = None
            return known_paths

        def addsitedir(sitedir, known_paths=None):
            """Add 'sitedir' argument to sys.path if missing and handle .pth files in
            'sitedir'"""
            if known_paths is None:
                known_paths = _init_pathinfo()
                reset = True
            else:
                reset = False
            sitedir, sitedircase = makepath(sitedir)
            if not sitedircase in known_paths:
                sys.path.append(sitedir)  # Add path component
                known_paths.add(sitedircase)
            try:
                names = os.listdir(sitedir)
            except OSError:
                return
            names = [name for name in names if name.endswith(".pth")]
            for name in sorted(names):
                addpackage(sitedir, name, known_paths)
            if reset:
                known_paths = None
            return known_paths

    addsitedir(site_packages)

    sys.real_prefix = sys.prefix
    sys.prefix = path
    # Move the added items to the front of the path:
    new_sys_path = []
    for item in list(sys.path):
        if item not in prev_sys_path:
            new_sys_path.append(item)
            sys.path.remove(item)
    sys.path[:0] = new_sys_path


current_environment = ""


# TODO: find all venvs; populate the venvs global
def initialize_venv():
    global current_environment
    create_environment("default")
    use_environment("default")
    current_environment = str(pathlib.Path(user_venv_dir, "default"))
