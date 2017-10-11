def test_msg():
    from .. import msg
    msg.logMessage('this', 'is', 'a', 'tests:', 42, level=msg.WARNING)
