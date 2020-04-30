class PluginType:
    is_singleton = False

    _name = None

    @classmethod
    def name(cls):
        return cls._name
