from qtpy.QtGui import QIcon

from xicam.core import msg
from xicam.plugins.settingsplugin import ParameterSettingsPlugin
from xicam.gui.static import path


class LoggingSettingsPlugin(ParameterSettingsPlugin):
    """Settings plugin for logging information and parameterization.
    """

    def __init__(self):
        def msg_levels(recommended=""):
            """Returns a dictionary mapping logging level names to their respective integer values.

            Note that `msg.levels` gives us the reverse mapping that we want, from level to level name.

            Parameters
            ----------
            recommended
                Optional string which will mark a logging level as recommended (for use in the list parameter)
                (default is "", which will not mark any levels).

            Returns
            -------
                Dictionary that maps log level names to their values, optionally with one name marked as recommended.

            """
            levels = dict()  # {v: k for k, v in msg.levels.items()}
            for level, level_name in msg.levels.items():
                if recommended and recommended == level_name:
                    levels[level_name + " (recommended)"] = level
                else:
                    levels[level_name] = level
            return levels

        super(LoggingSettingsPlugin, self).__init__(
            QIcon(str(path("icons/log.png"))),
            msg.LOGGING_SETTINGS_NAME,
            [
                # Show users where the log directory is, don't let them modify it though
                dict(
                    name="Log Directory",
                    value=msg.log_dir,
                    type="str",
                    readonly=True,
                    tip="Location where Xi-CAM writes its logs to.",
                ),
                # Allow users to configure the default log level for the xicam logger's FileHandler
                dict(
                    name=msg.FILE_LOG_LEVEL_SETTINGS_NAME,
                    values=msg_levels(recommended="DEBUG"),
                    value=msg.DEFAULT_FILE_LOG_LEVEL,
                    type="list",
                    tip="Changes how much information is logged to the log file in 'Log Directory.'",
                ),
                # Allow users to configure the default log level for the xicam logger's StreamHandler
                dict(
                    name=msg.STREAM_LOG_LEVEL_SETTINGS_NAME,
                    values=msg_levels(),
                    value=msg.DEFAULT_STREAM_LOG_LEVEL,
                    type="list",
                    tip="Changes how much information is logged to the system console / terminal.",
                ),
            ],
        )
        msg.file_handler.setLevel(self[msg.FILE_LOG_LEVEL_SETTINGS_NAME])
        msg.stream_handler.setLevel(self[msg.STREAM_LOG_LEVEL_SETTINGS_NAME])

    def apply(self):
        msg.file_handler.setLevel(self[msg.FILE_LOG_LEVEL_SETTINGS_NAME])
        msg.stream_handler.setLevel(self[msg.STREAM_LOG_LEVEL_SETTINGS_NAME])
