from xicam.plugins import ProcessingPlugin
from typing import Callable

# TODO: add debug flag that checks mutations by hashing inputs

class Workflow(object):
    def __init__(self, processes=None):
        self._processes = []
        self._observers = []
        if processes:
            self._processes.extend(processes)
        self.staged = False

    def addProcess(self, process: ProcessingPlugin, autoconnect: bool = False):
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
        self.update()
        # TODO: Add autoconnect functionality

    def insertProcess(self, index: int, process: ProcessingPlugin, autoconnect: bool = False):
        self._processes.insert(index, process)
        self.update()

    def removeProcess(self, process: ProcessingPlugin = None, index=None):
        if not process: process = self._processes[index]
        self._processes.remove(process)
        self.update()

    def autoConnectProcess(self, process: ProcessingPlugin):
        # for each input of given process
        for input in process.inputs:
            bestmatch = None
            matchness = None
            # Parse backwards from the given process, looking for matching outputs
            for process in reversed(self.processes[:self.processes.index(process)]):
                # check each output
                for output in process.outputs:
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

        # for each output of given process
        for output in process.outputs:
            bestmatch = None
            matchness = None
            # Parse backwards from the given process, looking for matching outputs
            for process in self.processes[self.processes.index(process) + 1:]:
                # check each output
                for input in process.inputs:
                    # if matching name
                    if output.name == input.name:
                        # if a name match hasn't been found
                        if matchness < 1:
                            bestmatch = input
                            matchness = 1
                            # if a name+type match hasn't been found
                            if output.type == input.type:
                                if matchness < 2:
                                    bestmatch = input
                                    matchness = 2
            if bestmatch:
                output.connect(bestmatch)


    def disableProcess(self, process):
        pass  # TODO: allow processes to be disabled

    @property
    def processes(self):
        return self._processes

    @processes.setter
    def processes(self, processes):
        self._processes = processes
        self.update()

    def connect(self, input, output):
        # Connect any two of the following: Input, Output, Signal, Slot
        # TODO: Allow connecting Process Inputs/Outputs or Signals/Slots
        pass

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

    def execute(self, connection):
        """
        Execute this workflow on the specified host. Connection will be a Connection object (WIP) keeping a connection
        to a compute resource, include connection.hostname, connection.username...

        Returns
        -------
        QThreadFuture
            A concurrent.futures-like qthread to monitor status. Returns True if successful

        """
        if not self.staged:
            self.stage(connection)
        # TODO: add execution path

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

    def detatch(self, observer: Callable):
        self._observers.remove(observer)

    def update(self):
        for observer in self._observers:
            observer()
