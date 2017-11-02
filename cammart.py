import json
from urllib import parse

import pip
import requests

from . import venvs


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
    o = requests.get(f'http://127.0.0.1:5000/pluginpackages/{name}')

    # Get the uri from the plugin package information
    uri = parse.urlparse(json.loads(o.content)["installuri"])

    # Install from the uri
    if uri.scheme == 'pipgit':  # Clones a git repo and installs with pip
        pip.main(["install", 'git+https://' + ''.join(uri[1:]), "--prefix", venvs.current_environment])
    elif uri.scheme == 'pip':
        pip.main(["install", ''.join(uri[1:]), "--prefix", venvs.current_environment])
    elif uri.scheme == 'conda':
        raise NotImplementedError
