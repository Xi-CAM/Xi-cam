from ProcessingPlugin import *

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

        for input in node.inputs.keys():
            for input_map in node.inputs[input].map_inputs:
              self.generate_graph(dsk, q, input_map[1].parent, mapped_node)
              args.append(input_map[1].parent.id)

        def function(q, args, func):
            class Args:
                def __init__(self, q, args):
                    pass

                def __setattr__(self, name, value):
                    pass

                def __getattr__(self, name):
                    return ""

            local_args = Args(q, args)

            try:
                 return func.evaluate(local_args)
            except:
                 return "Failure"

        dsk[node.id] = tuple([function, [q, args]])

    def convert_to_graph(self):
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
            wf = self.workflow_generator.convert(workflow)
            future = wf.execute()
            self.futures.append(future)


def test_workflow():
  class TomographyPlugin(WorkflowPlugin):
    class Task1(ProcessingPlugin):
        it1 = Input("it1")
        ot1 = Output("ot1")

        def __init__(self):
            super().__init__()
            pass

        def evaluate(self):
            pass

    class RealtimeTask(ProcessingPlugin):
        rit1 = Input("rit1")
        rot1 = Output("rot1")

        def __init__(self):
            super().__init__()
            pass

        def evaluate(self):
            pass

    class Task2(ProcessingPlugin):
        it2 = Input("it2")
        ot2 = Output("ot2")

        def __init__(self):
            super().__init__()
            pass

        def evaluate(self):
            pass

    def __init__(self):
        super(TomographyPlugin,self).__init__()
        tomo_wf = self.generate_workflow("Tomography")

        tomo_wf["task1"] = TomographyPlugin.Task1()
        tomo_wf["task2"] = TomographyPlugin.Task2()
        tomo_wf["rtask"] = TomographyPlugin.RealtimeTask()

        tomo_wf.task1.ot1.connect(tomo_wf.task2.it2)
        tomo_wf.rtask.rit1.subscribe(tomo_wf.task1.ot1)

        print(tomo_wf.convert_to_graph())

  test = TomographyPlugin()


