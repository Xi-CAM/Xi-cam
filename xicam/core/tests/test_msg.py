def test_msg():
    from xicam.core import msg

    msg.logMessage("this", "is", "a", "tests:", 42, level=msg.WARNING)


def test_exception_msg():
    from xicam.core import msg  # force load the message module
    import pytest

    # Raise an error; this should be
    with pytest.raises(Exception):
        raise RuntimeError("Something bad happened...")
