import pathlib


def path(item):
    return str(pathlib.Path(pathlib.Path(__file__).parent, item))
