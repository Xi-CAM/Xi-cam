from appdirs import user_config_dir, site_config_dir, user_cache_dir
import os

user_cache_dir = user_cache_dir(appname="xicam")
site_config_dir = site_config_dir(appname="xicam")
user_config_dir = user_config_dir(appname="xicam")

try:
    os.makedirs(user_cache_dir)
except FileExistsError:
    pass

try:
    os.makedirs(user_config_dir)
except FileExistsError:
    pass
