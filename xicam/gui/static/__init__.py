import pathlib
import sys


def path(item):
    if getattr(sys,'frozen',False):
        return item
    else:
        return str(pathlib.Path(pathlib.Path(__file__).parent, item))
