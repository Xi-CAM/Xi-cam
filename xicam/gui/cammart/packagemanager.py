import collections
import json
from urllib import parse
import os, sys
import pkg_resources
import requests
import yaml
from appdirs import user_config_dir, site_config_dir, user_cache_dir
import platform
import subprocess
from xicam.core import msg
from importlib import reload
import pip
from pathlib import Path

from . import venvs


def pipmain(args):
    old_env = os.environ.copy()
    os.environ["PYTHONPATH"] = os.path.join(venvs.current_environment, "Lib/site-packages")
    os.environ["PYTHONBASE"] = venvs.current_environment
    old_prefix = sys.prefix
    sys.prefix = venvs.current_environment

    r = 1  # (error code)
    try:
        # Install the bundled software

        try:
            r = pip.main(args)
        except AttributeError:
            from pip._internal import main

            r = main(args)
    except Exception as ex:
        msg.logError(ex)

    finally:
        os.environ = old_env
        sys.prefix = old_prefix
        return r

    # subprocess.call([os.path.join(venvs.current_environment, 'Scripts/pip.exe'), *args], env=env)
    # return 0  # Above subprocess typicall returns error code even though it succeeds


op_sys = platform.system()
if op_sys == "Darwin":  # User config dir incompatible with venv on darwin (space in path name conflicts)
    user_package_registry = Path(user_cache_dir(appname="xicam")) / "packages.yml"
else:
    user_package_registry = Path(user_config_dir(appname="xicam")) / "packages.yml"
site_package_registry = Path(site_config_dir(appname="xicam")) / "packages.yml"


def install(name: str):
    """
    Install a Xi-cam plugin package by querying the Xi-cam package repository with REST.

    Packages are installed into the currently active virtualenv

    Parameters
    ----------
    name : str
        The package name to be installed.
    """
    # TODO: test if installed
    # TODO: check if package is in repo

    # Get install plugin package information from cam-mart repository
    o = requests.get(f'http://cam.lbl.gov:5000/pluginpackages?where={{"name":"{name}"}}')

    # Get the uri from the plugin package information
    uri = parse.urlparse(json.loads(o.content)["_items"][0]["installuri"])

    failure = True

    print("Installing to:", venvs.current_environment)

    # Install from the uri
    if uri.scheme == "pipgit":  # Clones a git repo and installs with pip
        failure = pipmain(
            [
                "install",
                # f'--target={os.path.join(venvs.current_environment,"Lib/site-packages")}',
                "git+https://" + "".join(uri[1:]),
            ]
        )
    elif uri.scheme == "pip":
        failure = pipmain(
            [
                "install",
                # f'--target={os.path.join(venvs.current_environment,"Lib/site-packages")}',
                "".join(uri[1:]),
            ]
        )
    elif uri.scheme == "conda":
        raise NotImplementedError

    if not failure:
        pkg_registry[name] = uri.scheme

    from xicam.plugins import manager

    manager.collectPlugins()


def uninstall(name: str):
    # Note: pkg_resources keeps a "working_set" that won't normally be updated when venv changes...
    # An update may need to be forcefully triggered in the future
    pkg_resources._initialize_master_working_set()
    failure = True
    if name in pkg_registry:
        scheme = pkg_registry[name]
        if scheme in ["pipgit", "pip"]:
            failure = pipmain(["uninstall", "-y", name])
        elif scheme == "conda":
            raise NotImplementedError
    else:
        # TODO: Handle if name is not in the registry
        pass

    if not failure:
        del pkg_registry[name]

    return not failure


class pkg_registry(collections.MutableMapping):
    def __init__(self):
        self._store = dict()
        self.update(self._store)  # use the free update to set keys
        self.load()
        self.save()

    def __getitem__(self, key):
        return self._store[self.__keytransform__(key)]

    def __setitem__(self, key, value):
        self._store[self.__keytransform__(key)] = value
        self.save()

    def __delitem__(self, key):
        del self._store[self.__keytransform__(key)]
        self.save()

    def __iter__(self):
        return iter(self._store)

    def __len__(self):
        return len(self._store)

    def __keytransform__(self, key):
        return key

    def load(self):
        try:
            with open(user_package_registry, "r") as f:
                self._store = yaml.load(f.read())
        except FileNotFoundError:
            pass

    def save(self):
        user_package_registry.parent.mkdir(parents=True, exist_ok=True)
        with open(user_package_registry, "w") as f:
            f.write(yaml.dump(self._store))


pkg_registry = pkg_registry()

# def check_registry():
#
# def scan_for_unregistered():
#     unregistered_packages = {}
#     pkgs = pip.get_installed_distributions()
#     for pkg in pkgs:
#         targets = [pathlib.Path(pkg._provider.egg_info) / 'installed-files.txt',
#                    pathlib.Path(pkg._provider.egg_info) / 'RECORD']
#         for target in targets:
#             if target.exists():
#                 with open(str(target),'r') as f:
#                     if 'yapsy-plugin' in f.read():
#                         unregistered_packages[str(pathlib.Path(pkg.location)/pkg.key)] = pkg.project_name
#
#     return unregistered_packages
