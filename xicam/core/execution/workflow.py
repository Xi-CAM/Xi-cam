from xicam.plugins import OperationPlugin
from typing import Callable, List, Union, Tuple
from collections import defaultdict
from xicam.core import msg, execution
from xicam.core.threads import QThreadFuture, QThreadFutureIterator
from weakref import ref


# TODO: add debug flag that checks mutations by hashing inputs
class Graph(object):
    """Graph that represents operations as nodes and links as edges.

    This class is used as the underlying representation for a Workflow.

    Note that this is similar to a directed graph;
    however, this Graph allows multiple edges between two nodes,
    as there can be multiple outputs for operation A that link to
    multiple inputs for operation B.

    """

    def __init__(self):
        self._operations = []
        self._inbound_links = defaultdict(lambda: defaultdict(lambda: []))
        self._outbound_links = defaultdict(lambda: defaultdict(lambda: []))
        self._disabled_operations = set()

    def add_operation(self, operation: OperationPlugin):
        """Add a single operation into the workflow."""
        self.add_operations(operation)

    def add_operations(self, *operations: OperationPlugin):
        """Add operations into the workflow.

        This will add the list of operations to the end of the workflow.
        """
        # NOTE: Because of some Pycharm bugs, class-decorators break type inspection; expect to get complaints
        #       https://youtrack.jetbrains.com/issue/PY-27142
        for operation in operations:
            self.insert_operation(len(self._operations) + 1, operation)

    def insert_operation(self, index: int, operation: OperationPlugin):
        """Insert an operation at a specific index in the workflow.

        Parameters
        ----------
        index : int
            Index where to insert the operation. 0 will add at the beginning; -1 will add to the end.
        operation : OperationPlugin
            Operation to insert.
        """
        if not isinstance(operation, OperationPlugin):
            raise TypeError(f'Expected "{operation}" to be an OperationPlugin')
        self._operations.insert(index, operation)
        operation._workflow = ref(self)

        self.notify()

    def _validate_link_parameters(self, source, dest, source_param, dest_param):
        if not isinstance(source, OperationPlugin):
            raise TypeError(f'Expected source "{source}" to be an OperationPlugin')
        if not isinstance(dest, OperationPlugin):
            raise TypeError(f'Expected dest "{dest}" to be an OperationPlugin')
        if not isinstance(source_param, str):
            raise TypeError(f'Expected source_param "{source_param}" to be a string')
        if not isinstance(dest_param, str):
            raise TypeError(f'Expected dest_param "{dest_param}" to be a string')
        if source not in self._operations:
            raise ValueError(f'Source operation "{source}" cannot be found')
        if dest not in self._operations:
            raise ValueError(f'Destination operation "{dest}" cannot be found')

    def add_link(self, source, dest, source_param, dest_param):
        """Add a link between two operations in the workflow.

        Links are defined from an operation's parameter to another operation's parameter.
        This creates a connection between two operations during execution of a workflow.

        Parameters
        ----------
        source : OperationPlugin
            The operation to link from.
        dest : OperationPlugin
            The operation to link to.
        source_param : str
            Name of the parameter in the source operation to link (source of the data; output).
        dest_param : str
            Name of the parameter in the destination operation to link (where the data goes; input).
        """
        self._validate_link_parameters(source, dest, source_param, dest_param)

        if source_param not in source.output_names:
            raise ValueError(f'An output named "{source_param}" could not be found in the source operation, {source.name}')
        elif dest_param not in dest.input_names:
            raise ValueError(f'An input named "{dest_param}" could not be found in the destination operation, {dest.name}')
        self._inbound_links[dest][source].append((source_param, dest_param))
        self._outbound_links[source][dest].append((source_param, dest_param))

        self.notify()

    def remove_link(self, source, dest, source_param, dest_param):
        """Remove a link between two operations.

        Parameters
        ----------
        source : OperationPlugin
            The source operation to remove a link from.
        dest : OperationPlugin
            The destination operation to remove a link from.
        source_param : str
            Name of the source parameter that is defining the link to remove.
        dest_param : str
            Name of the destination parameter that is defining the link to remove.
        """
        self._validate_link_parameters(source, dest, source_param, dest_param)

        inbound_links = self._inbound_links[dest][source]
        outbound_links = self._outbound_links[source][dest]
        link = (source_param, dest_param)
        if link not in inbound_links:
            raise ValueError(f"There is no inbound link '{link}' to remove for source '{source}', dest '{dest}'")
        if link not in outbound_links:
            raise ValueError(f"There is no outbound link '{link}' to remove for source '{source}', dest '{dest}'")
        inbound_links.remove((source_param, dest_param))
        if len(inbound_links) == 0:
            del self._inbound_links[dest]
        outbound_links.remove((source_param, dest_param))
        if len(outbound_links) == 0:
            del self._outbound_links[source]

        self.notify()

    def get_inbound_links(self, operation):
        """Returns the links connected to the operation given (linked inputs of the operation).

        The returned dict represents all operations that are connected to `operation`.
        Links are represented as a list of 2-element tuples,
        where the first element of the tuple is another operation's output parameter,
        and the second element of the tuple is `operation`'s input parameter.

        Using `keys()` will give all of the operations that connect to `operation`.
        Using `values()` will give all of the links from each operation to `operation`.

        Parameters
        ----------
        operation : OperationPlugin
            Operation to get incoming links for (some operation -> `operation`).

        Returns
        -------
        defaultdict
            Returns a dictionary defining all of the links from any connected operations to `operation`.
        """
        if not isinstance(operation, OperationPlugin):
            raise TypeError(f"Expected an operation (got {operation} of type {type(operation)}")
        try:
            return self._inbound_links[operation]
        except KeyError as e:
            raise KeyError(f"Operation {operation} (named {operation.name} not found in inbound links")

    def get_outbound_links(self, operation):
        """Returns the links connected from the operation given (linked outputs of the operation).

        The returned dict represents all the operations that `operation` connects to.
        Links are represented as a list of 2-element tuples,
        where the first element of the tuple is `operation`'s output parameter,
        and the second element of the tuple is another operation's input parameter.

        Using `.keys()` on the returned dict will give all of the operations that `operation` connects to.
        Using `.values()` on the returned dict will give all of the links from `operation` to each operation.

        Parameters
        ----------
        operation : OperationPlugin
            Operation to get outgoing links for (`operation` -> some operation).

        Returns
        -------
        defaultdict
            Returns a dictionary defining all of the links from `operation` to any connected operations.
        """
        if not isinstance(operation, OperationPlugin):
            raise TypeError(f"Expected an operation (got {operation} of type {type(operation)}")
        try:
            return self._outbound_links[operation]
        except KeyError as e:
            raise KeyError(f"Operation {operation} (named {operation.name} not found in outbound links")

    def clear_operation_links(self, operation, clear_outbound=True, clear_inbound=True):
        """Remove all links for an operation."""

        # TODO : clear_outbound, clear_inbound
        if not isinstance(operation, OperationPlugin):
            raise TypeError(f"Expected '{operation}' to be an OperationPlugin")
        try:
            self._inbound_links[operation].clear()
            self._outbound_links[operation].clear()

            for op, value in self._inbound_links.items():
                if operation in self._inbound_links[op]:
                    del self._inbound_links[op][operation]

            for op, value in self._outbound_links.items():
                if operation in self._outbound_links[op]:
                    del self._outbound_links[op][operation]

            self.notify()

        except KeyError as e:
            raise KeyError(f"Operation {operation} (named {operation}) not found")

    def clear_links(self):
        """Remove all links from the workflow, but preserve the operations."""
        self._inbound_links.clear()
        self._outbound_links.clear()

        self.notify()

    def clear_operations(self):
        """Remove all operations and links from the workflow."""
        self._operations.clear()
        self._inbound_links.clear()
        self._outbound_links.clear()

        self.notify()

    def remove_operation(self, operation, remove_orphan_links=True):
        """Remove an operation from the workflow.

        Parameters
        ----------
        operation : OperationPlugin
            Operation to remove from the workflow.
        remove_orphan_links : bool
            If True, removes all links that link to the operation to be removed.
            If False, does not remove any links for the operation
            and returns the removed operations links dict (default is True).

        Returns
        -------
        defaultdict
            By default (`remove_orphan_links` is True), returns None.
            Otherwise, returns the links for the removed operation.
        """
        if not isinstance(operation, OperationPlugin):
            raise TypeError(f"Expected an operation (got {operation} of type {type(operation)}")

        try:
            self._operations.remove(operation)
        except ValueError as e:
            raise ValueError(f"Operation {operation} (named {operation.name} found")

        if remove_orphan_links:
            self.clear_operation_links(operation)
        else:
            return self.get_inbound_links(operation), self.get_outbound_links(operation)

        self.notify()

    def _end_operations(self):
        """
        find tasks at the end of the graph and work up
        check inputs and remove dependency nodes, what is left is unique ones
        """

        end_tasks = set(self.operations) - self._outbound_links.keys()

        msg.logMessage("End tasks:", *[task.name for task in end_tasks], msg.DEBUG)
        return end_tasks

    def _dask_graph(self):
        dask_graph = {}

        for operation in self.operations:
            links = {}
            dependent_ids = []
            for dep_operation, inbound_links in self._inbound_links[operation].items():
                for (source_param, dest_param) in inbound_links:
                    links[dest_param] = source_param
                dependent_ids.append(dep_operation.id)

            node = _OperationWrapper(operation, links)
            dask_graph[operation.id] = (node, *dependent_ids)

        return dask_graph

    def as_dask_graph(self):
        """
        process from end tasks and into all dependent ones

        Returns a tuple that represents the graph as a dask-compatible
        graph for processing. The second element of the tuple identifies
        the end node ids (i.e. nodes that do not have connected outputs).

        Returns
        -------
        tuple
            A tuple with two-elements, the first being the dask graph,
            the second being the end task ids.
        """

        for (i, node) in enumerate(self.operations):
            node.id = str(i)

        end_tasks = self._end_operations()

        dask_graph = self._dask_graph()
        end_task_ids = [i.id for i in end_tasks]

        return dask_graph, end_task_ids

    @property
    def operations(self):
        """Returns the operations of this workflow."""
        return self._operations

    def links(self):
        """Returns all the links defined in the workflow.

        Returns a list of tuples, each tuple representing a link as follows:
        source operation, destination operation, source parameter, destination parameter.

        Note that the links are shown as outbound links.

        Returns
        -------
        list
            Returns a list of the links (defined as outbound links) in the workflow.

        """
        return [
            (src, dest, link[0], link[1])
            for src, outbound_links in self._outbound_links.items()
            for dest, links in outbound_links.items()
            for link in links
        ]

    def operation_links(self, operation: OperationPlugin):
        """Returns the outbound links for an operation.

        Returns a list of tuples, each tuple representing a link as follows:
        `operation`, destination operation, `operation` source parameter, destination parameter.

        Returns
        -------
        list
            Returns a list of the links (defined as outbound links) for `operation`.
        """
        if not isinstance(operation, OperationPlugin):
            raise TypeError(f"Expected {operation} to be an OperationPlugin")
        if operation not in self.operations:
            raise ValueError(f'Operation "{operation}" not found')
        return [
            (operation, dest, link[0], link[1]) for dest, links in self._outbound_links[operation].items() for link in links
        ]

    def disabled_operations(self):
        """Returns the disabled operations (if any) in the workflow."""
        return self._disabled_operations

    def disabled(self, operation):
        """Indicate if the operation is disabled in the workflow.

        Parameters
        ----------
        operation : OperationPlugin
            Operation to check if it is disabled or not.

        Returns
        -------
        bool
            Returns True if the operation is disabled in the Workflow; otherwise False.
        """
        return operation in self._disabled_operations

    def set_disabled(
        self, operation: OperationPlugin, value: bool = True, remove_orphan_links: bool = True, auto_connect_all: bool = True
    ):
        """Set an operation's disabled state in the workflow.

        By default when disabling an operation, links connected to the operation will be removed
        (`remove_orphan_links` would be True).
        If `value` is False (re-enabling an operation), then no links are changed.

        Parameters
        ----------
        operation : OperationPlugin
            The operation whose disabled state is being modified.
        value : bool
            Indicates the disabled state (default is True, which disables the operation).
        remove_orphan_links : bool
            If True and `value` is True, removes the links connected to the operation.
            Otherwise, no links are changed (default is True).
        auto_connect_all : bool
            If True, then a best-effort attempt will be made to try to reconnect the
            operations in the workflow (default is True).
            See the `Graph.auto_connect_all` method for more information.
        Returns
        -------
        list
            Returns a list of any orphaned links for an operation that is set to disabled.
            Default behavior will return an empty list (when `remove_orphan_links` is True).
            If enabling an operation (`value` is False), then an empty list is returned,
            as no links are changed.
        """
        if value:
            self._disabled_operations.add(operation)
        else:
            if operation in self._disabled_operations:
                self._disabled_operations.remove(operation)

        orphaned_links = []
        if value:
            if remove_orphan_links:
                self.clear_operation_links(operation)
            else:
                orphaned_links = self.operation_links(operation)

        if auto_connect_all:
            self.auto_connect_all()

        self.notify()
        return orphaned_links

    def toggle_disabled(self, operation: OperationPlugin, remove_orphan_links=True, auto_connect_all=True):
        """Toggle the disable state of an operation.

        By default, when an operation is toggled to a disabled state,
        any links connected to the operation will be removed.

        Parameters
        ----------
        operation : OperationPlugin
            The operation to toggle disable state for.
        remove_orphan_links : bool
            If True, when the operation's toggle state is toggled to disabled,
            any links connected to the operation will be removed (default is True).

        Returns
        -------
        list
            Returns a list of any orphaned links for an operation.
            Default behavior will return an empty list.
            A non-empty list can be returned when `remove_orphan_links` is False
            and the connected operation is toggled to disabled.

        """
        is_disabled = False
        if operation in self._disabled_operations:
            is_disabled = True
        return self.set_disabled(operation, not is_disabled, remove_orphan_links, auto_connect_all)

    def auto_connect_all(self):
        """Attempts to automatically connect operations together by matching output names and input names.

        Makes a best-effort to link operations based on the names of their outputs and inputs.
        If operation A has an output named "image", and operation B has an input named "image",
        then A "image" will link to B "image".
        Outputs and inputs that have matching types in addition to matching names
        will be favored more for the auto-connection.

        If there are no outputs with matching inputs (by name), no links will be added.
        """
        self.clear_links()

        # for each operation
        for input_operation in self.operations:

            # for each input of given operation
            for input_name in input_operation.input_names:
                bestmatch = None
                matchness = 0
                # Parse backwards from the given operation, looking for matching outputs
                for output_operation in reversed(self.operations[: self.operations.index(input_operation)]):
                    # check each output
                    for output_name in output_operation.output_names:
                        # if matching name
                        if output_name == input_name:
                            # if a name match hasn't been found
                            if matchness < 1:
                                bestmatch = output_operation, output_name
                                matchness = 1
                                # if a name+type match hasn't been found
                                if output_operation.output_types[output_name] == input_operation.input_types[input_name]:
                                    if matchness < 2:
                                        bestmatch = output_operation, output_name
                                        matchness = 2
                if bestmatch:
                    self.add_link(bestmatch[0], input_operation, bestmatch[1], input_name)
                    msg.logMessage(
                        f"connected {bestmatch[0].name}:{bestmatch[1]} to {input_operation.name}:{input_name}",
                        level=msg.DEBUG,
                    )

    def notify(self, *args, **kwargs):
        """See Workflow.notify"""
        pass

    def _pretty_print(self):
        """Print out links in easy-to-read format."""

        def print_underlined(text):
            underline = "-" * len(text)
            print(f"{text}\n{underline}")

        print_underlined("Graph:")
        # Assumes a link has the following structure:
        # tuple(source operation, destination operation, source parameter, destination parameter)
        for link in self.links():
            source = link[0]
            dest = link[1]
            source_param = link[2]
            dest_param = link[3]
            print(f"\t({source.name})[{source_param}] ---> [{dest_param}]({dest.name})")

        print_underlined("Inbound links:")
        for op, link in self._inbound_links.items():
            for source, l in dict(link).items():
                print(f"\t({op.name}) from ({source.name}) via {l}")

        print_underlined("Outbound links:")
        for op, link in self._outbound_links.items():
            for dest, l in dict(link).items():
                print(f"\t({op.name}) to ({dest.name}) via {l}")


class _OperationWrapper:
    def __init__(self, node, named_args, islocal=False):
        self.node = node
        self.named_args = named_args
        self.islocal = islocal
        self.queues_in = {}
        self.queues_out = {}

        self.node.__internal_data__ = self

    # args = [{'name':value}]

    def __call__(self, *args):
        node_args = {}
        for arg, (input_name, sender_operation_name) in zip(args, self.named_args.items()):
            node_args[input_name] = arg[sender_operation_name]

        result_keys = self.node.output_names
        result_values = self.node(**node_args)
        if not isinstance(result_values, tuple):
            result_values = (result_values,)

        return dict(zip(result_keys, result_values))

    def __repr__(self):
        # return getattr(self.node, "name", self.node.__class__.__name__)
        return self.node.__class__.__name__


class Workflow(Graph):
    def __init__(self, name="", operations=None):
        """
        Create a Workflow that can be executed.

        Parameters
        ----------
        name : str, optional
            Name of the Workflow (default is "").
        operations : List, optional
            List of operations to add to the Workflow being created (default is None).
        """
        super(Workflow, self).__init__()
        # self._operations = []  # type: List[OperationPlugin]
        self._observers = set()
        # self._links = []  # type: List[Tuple[ref, str, ref, str]]
        if name:
            self.name = name

        if operations:
            # self._operations.extend(operations)
            self.add_operations(*operations)
        self.staged = False

        self.lastresult = []

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
        # TODO: Operations invalidate parent workflow staged attribute if data resources are modified, but not parameters
        # TODO: check if data is accessible from compute resource; if not -> copy data to compute resource
        # TODO: use cam-link to mirror installation of plugin packages

    def execute(
        self,
        executor=None,
        connection=None,
        callback_slot=None,
        finished_slot=None,
        except_slot=None,
        default_exhandle=True,
        lock=None,
        fill_kwargs=True,
        threadkey=None,
        **kwargs,
    ):
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
            self.fill_kwargs(**kwargs)

        if executor is None:
            executor = execution.executor

        future = QThreadFuture(
            executor.execute,
            self,
            callback_slot=callback_slot,
            finished_slot=finished_slot,
            except_slot=except_slot,
            default_exhandle=default_exhandle,
            lock=lock,
            threadkey=threadkey,
        )
        future.start()
        return future

    def execute_synchronous(self, executor=None, connection=None, fill_kwargs=True, **kwargs):
        if not self.staged:
            self.stage(connection)

        if fill_kwargs:
            self.fill_kwargs(**kwargs)

        if executor is None:
            executor = execution.executor

        return executor.execute(self)

    def execute_all(
        self,
        connection=None,
        executor=None,
        callback_slot=None,
        finished_slot=None,
        except_slot=None,
        default_exhandle=True,
        lock=None,
        fill_kwargs=True,
        threadkey=None,
        **kwargs,
    ):
        """
        Execute this workflow on the specified host. Connection will be a Connection object (WIP) keeping a connection
        to a compute resource, include connection.hostname, connection.username...

        Each kwargs is expected to be an iterable of the same length; these values will be iterated over, zipped, and
        executed through the workflow.

        Returns
        -------
        QThreadFuture
            A concurrent.futures-like qthread to monitor status. The future's callback_slot receives the result.

        """
        if not self.staged:
            self.stage(connection)

        if executor is None:
            executor = execution.executor

        def executeiterator(workflow):
            for kwargvalues in zip(*kwargs.values()):
                zipkwargs = dict(zip(kwargs.keys(), kwargvalues))
                if fill_kwargs:
                    self.fill_kwargs(**zipkwargs)
                yield (executor.execute)(workflow)

        future = QThreadFutureIterator(
            executeiterator,
            self,
            callback_slot=callback_slot,
            finished_slot=finished_slot,
            except_slot=except_slot,
            default_exhandle=default_exhandle,
            lock=lock,
            threadkey=threadkey,
        )
        future.start()
        return future

    def fill_kwargs(self, **kwargs):
        """
        Fills in all empty inputs with names matching keys in kwargs.
        """
        for operation in self.operations:
            for key in kwargs:
                if key in operation.input_names:
                    operation.filled_values[key] = kwargs[key]

    def validate(self):
        """
        Validate all of:\
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
        """Add an observer to the Workflow.

        An observer is a callable that is called when the Workflow.notify
        method is called. In other words,
        the observer will be called whenever the Workflow state changes;
        for example, links are modified, operations are removed, etc.
        When notified, the observer is called.

        Parameters
        ----------
        observer : Callable
            A callable to add from the Workflow.
        """
        self._observers.add(observer)

    def detach(self, observer: Callable):
        """Remove an observer from the Workflow.

        An observer is a callable that is called when the Workflow.notify
        method is called. In other words,
        the observer will be called whenever the Workflow state changes;
        for example, links are modified, operations are removed, etc.
        When notified, the observer is called.

        Parameters
        ----------
        observer : Callable
            The callable to remove from the Workflow.
        """
        if observer in self._observers:
            self._observers.remove(observer)

    def notify(self):
        """Notify the observers; the observers will be called.
        """
        for observer in self._observers:
            observer()

    @property
    def hints(self):
        hints = []
        for operation in self._operations:
            hints.extend(operation.hints)
        return hints

    def visualize(self, canvas, **canvases):
        canvasinstances = {name: canvas() if callable(canvas) else canvas for name, canvas in canvases.items()}
        for operation in self._operations:
            for hint in operation.hints:
                hint.visualize(canvas)
