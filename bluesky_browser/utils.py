from traitlets import TraitType
from traitlets.config.loader import (PyFileConfigLoader, ConfigFileNotFound,
                                     Config)

CONFIG_FILE_NAME = 'bluesky_browser_config.py'
CONFIG_SEARCH_PATH = ('.')


def load_config():
    loader = PyFileConfigLoader(CONFIG_FILE_NAME, CONFIG_SEARCH_PATH)
    try:
        config = loader.load_config()
    except ConfigFileNotFound:
        config = Config()
    return config


class Callable(TraitType):
    """A trait which is callable.
    Notes
    -----
    Classes are callable, as are instances
    with a __call__() method."""

    info_text = 'a callable'

    def validate(self, obj, value):
        if callable(value):
            return value
        else:
            self.error(obj, value)
