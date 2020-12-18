import os
import pytest
from pytestqt import qtbot
from xicam.core.tests.workflow_fixtures import simple_workflow, square_op, sum_op


@pytest.mark.skipif(os.getenv("CI") is not None, reason="Core dumps on github actions")
def test_daskflow(qtbot, simple_workflow):


    from pyqtgraph.flowchart import Node, Terminal

    # COREDUMPS HERE!
    a = Terminal(Node("test1"), "test1", "in")

    from xicam.gui.widgets.daskflow import DaskFlow

    df = DaskFlow()
    df.fromDask(simple_workflow)

    qtbot.addWidget(df)
