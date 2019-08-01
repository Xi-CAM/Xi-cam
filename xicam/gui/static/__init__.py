import pathlib
import sys


def path(item: str):
    return str(pathlib.Path(pathlib.Path(__file__).parent, item))
