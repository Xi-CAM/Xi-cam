from pytestqt import qtbot

def test_daskflow(qtbot):


    from pyqtgraph.flowchart import Node, Terminal

    # COREDUMPS HERE!
    a = Terminal(Node("test1"), "test1", "in")

    from xicam.gui.widgets.daskflow import DaskFlow
    from xicam.SAXS.calibration.workflows import FourierCalibrationWorkflow

    df = DaskFlow()
    workflow = FourierCalibrationWorkflow()
    df.fromDask(workflow)

    qtbot.addWidget(df)