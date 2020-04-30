import argparse
from functools import lru_cache


class _RaisingAruementParser(argparse.ArgumentParser):
    """Raise instead of exit on failure to parse arguments

    This is because we need to parse at import in xicam.plugin but
    should be forgiving of importing in contexts other than the
    canonical xicam application.

    We must parse on import because we use CLI flags to controls if
    camart is enabled in the `__init__` of
    xicam.plugin.XicamPluginManager which we then instatiate on import.

    This singleton is then imported many other places.

    This class should be removed when we remove the need to parse on
    import.

    """

    _orig_error = argparse.ArgumentParser.error

    def error(self, message):
        raise RuntimeError(message)


@lru_cache()
def parse_args(exit_on_fail=True):
    parser = _RaisingAruementParser()
    parser.add_argument("-v", "--verbose", dest="verbose", action="count", help="increase output verbosity", default=0)
    parser.add_argument(
        "--no-cammart", dest="nocammart", action="store_true", help="disable cammart and sandboxed environment features"
    )
    parser.add_argument(
        "--blacklist",
        dest="blacklist",
        action="append",
        help="prevent Xi-cam from loading a plugin by name",
        type=str,
        default=[],
    )
    parser.add_argument("--no-splash", dest="nosplash", action="store_true", help="skip the Xi-cam splash screen")
    try:
        return parser.parse_args()
    except RuntimeError as re:
        if exit_on_fail:
            parser._orig_error(str(re))
        else:
            raise
