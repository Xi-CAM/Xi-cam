import pathlib


def path(item):
    return pathlib.Path(pathlib.Path(__file__).parent, item)
