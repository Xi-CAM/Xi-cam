import pathlib
from typing import Union

import fabio


def loadDoc(filename: Union[str, pathlib.Path] = None, uuid: str = None):
    """
    Load a document object, either from a file source or a databroker source, by uuid. If loading from a filename, the
    file will be registered in databroker.

    Parameters
    ----------
    filename
    uuid

    Returns
    -------

    """

    if filename:
        f = fabio.open(str(filename))
