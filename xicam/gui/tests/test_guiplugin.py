from qtpy.QtWidgets import QLabel
from xicam.plugins import GUIPlugin, GUILayout


class TestPlugin(GUIPlugin):
    name = "test"

    def __init__(self):
        self.stages = {
            "Stage 1": GUILayout(QLabel("Stage 1")),
            "Stage 2": {"Stage 2.1": GUILayout(QLabel("Stage 2"))},
            "Stage 3": {"Stage 3.1": GUILayout(QLabel("Stage 3.1")), "Stage 3.2": GUILayout(QLabel("Stage 3.2"))},
        }

        super(TestPlugin, self).__init__()
