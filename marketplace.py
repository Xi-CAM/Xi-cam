def install(packagename):
    if isInstalled(packagename): return True


def isInstalled(packagename):
    try:
        __import__(packagename)
    except ImportError:
        return False
    else:
        return True
