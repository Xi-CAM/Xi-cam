from appdirs import user_config_dir, site_config_dir, user_cache_dir
import os
import platform


user_cache_dir = user_cache_dir(appname="xicam")
site_config_dir = site_config_dir(appname="xicam")
user_config_dir = user_config_dir(appname="xicam")
user_dev_dir = os.path.expanduser("~/Xi-cam/plugins")
op_sys = platform.system()
if op_sys == "Darwin":  # User config dir incompatible with venv on darwin (space in path name conflicts)
    user_plugin_dir = os.path.join(user_cache_dir, "plugins")
else:
    user_plugin_dir = os.path.join(user_config_dir, "plugins")
site_plugin_dir = os.path.join(site_config_dir, "plugins")


def init_dir(path):
    try:
        os.makedirs(path)
    except FileExistsError:
        pass


def init_dirs():
    for path in [user_cache_dir, user_config_dir, user_plugin_dir, user_dev_dir]:
        init_dir(path)
