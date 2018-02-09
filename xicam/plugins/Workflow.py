from ProcessingPlugin import *

class WorkflowProcess():
  def __init__(self, node, named_args, islocal=False):
    self.node = node
    self.named_args = named_args
    self.islocal = islocal
    self.queues_in = {}
    self.queues_out = {}

    self.node.__internal_data__ = self

  def __call__(self, args):

    if args is not None and len(args) > 0:
        for i in range(len(args)):
            self.node.inputs[self.named_args[i]].value = args[i][0].value

    self.node.evaluate()

    outputs = []
    for i in self.node.outputs.keys():
       outputs.append(self.node.outputs[i])

    return outputs

class Workflow():
    def __init__(self, name):
        self.name = name
        self.nodes = {}

    def __setitem__(self, key, item):
        item.workflow = self
        self.nodes[key] = item
        self.__dict__[key] = item

    def __getitem__(self, key):
        return self.nodes[key]

    def addProcess(self, process):
        return self.__setitem__(process.__class__.__name__, process)

    def find_end_tasks(self):
        """
        find tasks at the end of the graph and work up
        check inputs and remove dependency nodes, what is left is unique ones
        """

        is_dep_task = []

        for node in self.nodes.values():
            for input in node.inputs.keys():
                for im in node.inputs[input].map_inputs:
                    is_dep_task.append(im[1].parent)

        end_tasks = list(self.nodes.values()).copy()

        for dep_task in is_dep_task:
            if dep_task in end_tasks:
                end_tasks.remove(dep_task)

        return end_tasks

        def generate_graph(self, dsk, q, node, mapped_node):

        if node in mapped_node:
            return

        mapped_node.append(node)

        args = []
        named_args = []

        for input in node.inputs.keys():
            for input_map in node.inputs[input].map_inputs:
              self.generate_graph(dsk, q, input_map[1].parent, mapped_node)
              args.append(input_map[1].parent.id)
              named_args.append(input_map[0]) # TODO test to make sure output is in input

        workflow = WorkflowProcess(node, named_args)

        dsk[node.id] = tuple([workflow, args])

    def convert_graph(self):
        """
        process from end tasks and into all dependent ones
        """

        for (i, node) in enumerate(self.nodes.values()):
            node.id = str(i)

        end_tasks = self.find_end_tasks()

        dsk = {}
        mapped_node = []
        q = None

        for task in end_tasks:
            self.generate_graph(dsk, q, task, mapped_node)

        return (dsk, end_tasks)

class WorkflowPlugin(ProcessingPlugin):
    name = 'Workflow'

    def __init__(self, *args, **kwargs):
        self.workflows = []

        # self.workflow_generator = DaskWorkflowGenerator()
        super(WorkflowPlugin, self).__init__(*args, **kwargs)

    def generate_workflow(self, name):
        workflow = Workflow(name)
        self.workflows.append(workflow)
        return workflow

    def evaluate():
        if self.workflow_generator is None:
            return

        for workflow in self.workflows:
            wf = self.workflow_generator.convert_graph(workflow)
            future = wf.execute()
            self.futures.append(future)

def test_SAXSWorkflow():
    from pyFAI.detectors import Pilatus2M
    import numpy as np
    from pyFAI import AzimuthalIntegrator, units
    from scipy.ndimage import morphology
    import fabio

    class ThresholdMaskPlugin(ProcessingPlugin):
        data = Input(description='Frame image data',
                     type=np.ndarray)
        minimum = Input(description='Threshold floor',
                        type=int)
        maximum = Input(description='Threshold ceiling',
                        type=int)
        neighborhood = Input(
            description='Neighborhood size in pixels for morphological opening. Only clusters of this size'
                        ' that fail the threshold are masked',
            type=int)
        mask = Output(description='Thresholded mask (1 is masked)',
                      type=np.ndarray)

        def evaluate(self):
            self.mask.value = np.logical_or(self.data.value < self.minimum.value, self.data.value > self.maximum.value)

            y, x = np.ogrid[-self.neighborhood.value:self.neighborhood.value + 1,
                   -self.neighborhood.value:self.neighborhood.value + 1]
            kernel = x ** 2 + y ** 2 <= self.neighborhood.value ** 2

            morphology.binary_opening(self.mask.value, kernel, output=self.mask.value)  # write-back to mask

    class QIntegratePlugin(ProcessingPlugin):
        integrator = Input(description='A PyFAI.AzimuthalIntegrator object',
                           type=AzimuthalIntegrator)
        data = Input(description='2d array representing intensity for each pixel',
                     type=np.ndarray)
        npt = Input(description='Number of bins along q')
        polz_factor = Input(description='Polarization factor for correction',
                            type=float)
        unit = Input(description='Output units for q',
                     type=[str, units.Unit],
                     default="q_A^-1")
        radial_range = Input(
            description='The lower and upper range of the radial unit. If not provided, range is simply '
                        '(data.min(), data.max()). Values outside the range are ignored.',
            type=tuple)
        azimuth_range = Input(
            description='The lower and upper range of the azimuthal angle in degree. If not provided, '
                        'range is simply (data.min(), data.max()). Values outside the range are ignored.')
        mask = Input(description='Array (same size as image) with 1 for masked pixels, and 0 for valid pixels',
                     type=np.ndarray)
        dark = Input(description='Dark noise image',
                     type=np.ndarray)
        flat = Input(description='Flat field image',
                     type=np.ndarray)
        method = Input(description='Can be "numpy", "cython", "BBox" or "splitpixel", "lut", "csr", "nosplit_csr", '
                                   '"full_csr", "lut_ocl" and "csr_ocl" if you want to go on GPU. To Specify the device: '
                                   '"csr_ocl_1,2"',
                       type=str)
        normalization_factor = Input(description='Value of a normalization monitor',
                                     type=float)
        q = Output(description='Q bin center positions',
                   type=np.array)
        I = Output(description='Binned/pixel-split integrated intensity',
                   type=np.array)

        def evaluate(self):
            self.q.value, self.I.value = self.integrator.value().integrate1d(data=self.data.value,
                                                                           npt=self.npt.value,
                                                                           radial_range=self.radial_range.value,
                                                                           azimuth_range=self.azimuth_range.value,
                                                                           mask=self.mask.value,
                                                                           polarization_factor=self.polz_factor.value,
                                                                           dark=self.dark.value,
                                                                           flat=self.flat.value,
                                                                           method=self.method.value,
                                                                           unit=self.unit.value,
                                                                           normalization_factor=self.normalization_factor.value)

    # create processes
    thresholdmask = ThresholdMaskPlugin()
    qintegrate = QIntegratePlugin()

    # set values
    def AI_func():
        from pyFAI.detectors import Pilatus2M
        from pyFAI import AzimuthalIntegrator, units
        return AzimuthalIntegrator(.283,5.24e-3, 4.085e-3,0,0,0,1.72e-4,1.72e-4,detector=Pilatus2M(),wavelength=1.23984e-10)

    # AI = AzimuthalIntegrator(.283,5.24e-3, 4.085e-3,0,0,0,1.72e-4,1.72e-4,detector=Pilatus2M(),wavelength=1.23984e-10)
    AI = AI_func
    thresholdmask.data.value = fabio.open('/Users/hari/Downloads/AGB_5S_USE_2_2m.edf').data
    qintegrate.integrator.value = AI
    qintegrate.npt.value = 1000
    thresholdmask.minimum.value = 30
    thresholdmask.maximum.value = 1e12

    qintegrate.data.value = fabio.open('/Users/hari/Downloads/AGB_5S_USE_2_2m.edf').data
    thresholdmask.neighborhood.value = 1
    qintegrate.normalization_factor.value = 0.5
    qintegrate.method.value = "numpy"

    # connect processes
    thresholdmask.mask.connect(qintegrate.mask)

    # add processes to workflow
    global wf
    wf = Workflow('QIntegrate')
    wf.addProcess(thresholdmask)
    wf.addProcess(qintegrate)

    return wf

class DaskWorkflow:
   def __init__(self):
      pass

   def execute(self, wf):
      import dask
      import distributed
      from distributed import Queue

      client = distributed.Client()

      dsk = wf.convert_graph()

      # generate queues
      for node in wf.nodes.keys():
        i = wf.nodes[node]
        for key in i.inputs.keys():
          j = i.inputs[key]
          for k in j.subscriptions:
            # share distributed Queue between sender and receiver
            q = Queue()
            j.__internal_data__.queues_in.append({j.name : q})
            k[1].parent.__internal_data__.queues_out.append({k[0].name : q})


      print("Running: ", dsk[0], dsk[1])
      result = client.get(dsk[0], dsk[1])

      res = {}
      for f in result:
        for f1 in f:
          res[f1.name] = f1.value

      return res

def test_SAXSWorkflow_Dask():
   wf = test_SAXSWorkflow()
   dsk = DaskWorkflow()
   result = dsk.execute(wf)
   print(result)

   """
   wf.nodes["ThresholdMaskPlugin"].evaluate()
   wf.nodes["ThresholdMaskPlugin"].evaluate()
   wf.nodes["QIntegratePlugin"].inputs["mask"].value = wf.nodes["ThresholdMaskPlugin"].outputs["mask"].value
   wf.nodes["QIntegratePlugin"].evaluate()
   print(wf.nodes["QIntegratePlugin"].outputs["q"].value)
   print(wf.nodes["QIntegratePlugin"].outputs["I"].value)
   """

