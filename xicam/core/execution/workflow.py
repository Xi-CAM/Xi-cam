from xicam.plugins import ProcessingPlugin
from typing import Callable, List
from .camlinkexecutor import CamLinkExecutor
from .localexecutor import LocalExecutor
from collections import OrderedDict
from xicam.core import msg
from xicam.gui.threads import QThreadFuture


# TODO: add debug flag that checks mutations by hashing inputs

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
                # self.node.inputs[self.named_args[i]].value = args[i][0].value
                for key in args[i].keys():
                    if key in self.named_args:
                        msg.logMessage(
                            f'Setting input {self.node.__class__.__name__}:{self.named_args[key]} to output {args[i][key].value}',
                            level=msg.DEBUG)
                        self.node.inputs[self.named_args[key]].value = args[i][key].value

        self.node.evaluate()

        return self.node.outputs

    def __repr__(self):
        return self.node.__class__.__name__


class Workflow(object):
    def __init__(self, name, processes=None):
        self._processes = []
        self._observers = []
        self.name = name

        if processes:
            self._processes.extend(processes)
        self.staged = False

        self.lastresult = []

    def findEndTasks(self):
        """
        find tasks at the end of the graph and work up
        check inputs and remove dependency nodes, what is left is unique ones
        """

        dependent_tasks = set()

        for process in self.processes:
            for input in process.inputs.values():
                for _, mapped_output in input.map_inputs:
                    dependent_tasks.add(mapped_output.parent)

        end_tasks = set(self.processes) - dependent_tasks

        msg.logMessage('End tasks:', *[task.name for task in end_tasks], msg.DEBUG)
        return end_tasks

    def generateGraph(self, dsk, node, mapped_node):
        """
        Recursive function that adds
        :param dsk:
        :param q:
        :param node:
        :param mapped_node:
        :return:
        """
        if node in mapped_node:
            return

        mapped_node.append(node)

        args = OrderedDict()
        named_args = {}

        for inp in node.inputs.keys():
            for input_map in node.inputs[inp].map_inputs:
                self.generateGraph(dsk, input_map[1].parent, mapped_node)
                args[input_map[1].parent.id] = None
                # named_args.append({input_map[1].name: input_map[0]})  # TODO test to make sure output is in input
                named_args[input_map[1].name] = input_map[0]

        workflow = WorkflowProcess(node, named_args)
        dsk[node.id] = tuple([workflow, list(reversed(args.keys()))])

    def convertGraph(self):
        """
        process from end tasks and into all dependent ones
        """

        for (i, node) in enumerate(self.processes):
            node.id = str(i)

        end_tasks = self.findEndTasks()

        graph = {}
        mapped_node = []

        for task in end_tasks:
            self.generateGraph(graph, task, mapped_node)

        return graph, [i.id for i in end_tasks]

    def addProcess(self, process: ProcessingPlugin, autoconnectall: bool = False):
        """
        Adds a Process as a child.
        Parameters
        ----------
        process:    ProcessingPlugin
            Process to add
        autowireup: bool
            If True, connects Outputs of the previously added Process to the Inputs of process, matching names and types
        """
        self._processes.append(process)
        process._workflow = self
        self.update()
        if autoconnectall: self.autoConnectAll()

    def insertProcess(self, index: int, process: ProcessingPlugin, autoconnectall: bool = False):
        self._processes.insert(index, process)
        process._workflow = self
        self.update()
        if autoconnectall: self.autoConnectAll()

    def removeProcess(self, process: ProcessingPlugin = None, index=None, autoconnectall=False):
        if not process: process = self._processes[index]
        process._workflow = None
        self._processes.remove(process)
        if autoconnectall: self.autoConnectAll()
        self.update()

    def autoConnectAll(self):
        self.clearConnections()

        # for each process
        for inputprocess in self.processes:

            # for each input of given process
            for input in inputprocess.inputs.values():
                bestmatch = None
                matchness = 0
                # Parse backwards from the given process, looking for matching outputs
                for outputprocess in reversed(self.processes[:self.processes.index(inputprocess)]):
                    # check each output
                    for output in outputprocess.outputs.values():
                        # if matching name
                        if output.name == input.name:
                            # if a name match hasn't been found
                            if matchness < 1:
                                bestmatch = output
                                matchness = 1
                                # if a name+type match hasn't been found
                                if output.type == input.type:
                                    if matchness < 2:
                                        bestmatch = output
                                        matchness = 2
                if bestmatch:
                    bestmatch.connect(input)
                    msg.logMessage(
                        f'connected {bestmatch.parent.__class__.__name__}:{bestmatch.name} to {input.parent.__class__.__name__}:{input.name}',
                        level=msg.DEBUG)

                    # # for each output of given process
                    # for output in process.outputs.values():
                    #     bestmatch = None
                    #     matchness = 0
                    #     # Parse backwards from the given process, looking for matching outputs
                    #     for process in self.processes[self.processes.index(process) + 1:]:
                    #         # check each output
                    #         for input in process.inputs.values():
                    #             # if matching name
                    #             if output.name == input.name:
                    #                 # if a name match hasn't been found
                    #                 if matchness < 1:
                    #                     bestmatch = input
                    #                     matchness = 1
                    #                     # if a name+type match hasn't been found
                    #                     if output.type == input.type:
                    #                         if matchness < 2:
                    #                             bestmatch = input
                    #                             matchness = 2
                    #     if bestmatch:
                    #         output.connect(bestmatch)

    def clearConnections(self):
        for process in self.processes:
            process.clearConnections()

    def toggleDisableProcess(self, process, autoconnectall=False):
        process.disabled = not process.disabled
        process.clearConnections()
        if autoconnectall: self.autoConnectAll()
        self.update()

    @property
    def processes(self) -> List[ProcessingPlugin]:
        return [process for process in self._processes if not process.disabled]

    @processes.setter
    def processes(self, processes):
        for process in self._processes:
            process._workflow = None

        self._processes = processes
        for process in processes:
            process._workflow = self
        self.update()

    def stage(self, connection):
        """
        Stages required data resources to the compute resource. Connection will be a Connection object (WIP) keeping a
        connection to a compute resource, include connection.hostname, connection.username...

        Returns
        -------
        QThreadFuture
            A concurrent.futures-like qthread to monitor status. Returns True if successful
        """
        self.staged = True
        # TODO: Processes invalidate parent workflow staged attribute if data resources are modified, but not parameters
        # TODO: check if data is accessible from compute resource; if not -> copy data to compute resource
        # TODO: use cam-link to mirror installation of plugin packages

    def execute(self, connection, callback_slot=None, finished_slot=None, except_slot=None, default_exhandle=True,
                lock=None, fill_kwargs=True, threadkey=None, **kwargs):
        """
        Execute this workflow on the specified host. Connection will be a Connection object (WIP) keeping a connection
        to a compute resource, include connection.hostname, connection.username...

        Returns
        -------
        QThreadFuture
            A concurrent.futures-like qthread to monitor status. The future's callback_slot receives the result.

        """
        if not self.staged:
            self.stage(connection)

        if fill_kwargs:
            self.fillKwargs(**kwargs)

        future = QThreadFuture(LocalExecutor().execute, self,
                               callback_slot=callback_slot,
                               finished_slot=finished_slot,
                               default_exhandle=default_exhandle,
                               lock=lock,
                               threadkey=threadkey)
        future.start()
        return future

    def fillKwargs(self, **kwargs):
        """
        Fills in all empty inputs with names matching keys in kwargs.
        """
        for process in self.processes:
            for key, input in process.inputs.items():
                if not input.map_inputs and key in kwargs:
                    input.value = kwargs[key]


    def validate(self):
        """
        Validate all of:
        - All required inputs are satisfied.
        - Connection is active.
        - ?

        Returns
        -------
        bool
            True if workflow is valid.

        """
        # TODO: add validation
        return True

    def attach(self, observer: Callable):
        self._observers.append(observer)

    def detach(self, observer: Callable):
        self._observers.remove(observer)

    def update(self):
        for observer in self._observers:
            observer()
