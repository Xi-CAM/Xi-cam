from xicam.plugins.Workflow import *


def test_SAXSWorkflow_Dask():
    from distributed import Client, LocalCluster, Scheduler, Worker
    s = Scheduler()
    s.start()
    w = Worker(scheduler_port=s.port, scheduler_ip=s.ip)
    w.start()

    Client(s.address)
    wf = test_SAXSWorkflow()
    dsk = DaskWorkflow()
    print(wf.convert_graph())

    result = dsk.execute(wf)
    # print(result)

    """
    wf.nodes["ThresholdMaskPlugin"].evaluate()
    wf.nodes["ThresholdMaskPlugin"].evaluate()
    wf.nodes["QIntegratePlugin"].inputs["mask"].value = wf.nodes["ThresholdMaskPlugin"].outputs["mask"].value
    wf.nodes["QIntegratePlugin"].evaluate()
    print(wf.nodes["QIntegratePlugin"].outputs["q"].value)
    print(wf.nodes["QIntegratePlugin"].outputs["I"].value)
    """
