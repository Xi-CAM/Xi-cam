class PluginType:
    is_singleton = False
    entrypoint_prefix = 'xicam.plugins.'

    _name = None

    @classmethod
    def name(cls):
        return cls._name
