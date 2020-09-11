"""
Nothing useful here!
Why?
Because with the PluginType Plugin, we need to register the SnifferPlugin as an entrypoint for the manager to
collect them. In this case, the only meaningful part is the name of the entrypoint, not what it points to. Of course,
it has to point to something, so...
"""
from .plugin import PluginType


class SnifferPlugin():
    """
    This is just to direct Xi-cam for how to load these plugins; its not intended to be instantiated or subclassed.
    """

    entrypoint_prefix = 'databroker.'
    needs_qt = False