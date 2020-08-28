import pytest
from pytestqt import qtbot
import io
import contextlib

from xicam.core import execution
from xicam.core.execution import localexecutor
from xicam.core.execution.workflow import Graph, Workflow
from xicam.plugins.operationplugin import output_names, operation

from xicam.core.tests.workflow_fixtures import a_op, b_op, c_op, graph, double_and_triple_op, sum_op, square_op, negative_op, simple_workflow


# Note that this test relies on the xicam.plugins module
# TODO prevent adding circular links
execution.executor = localexecutor.LocalExecutor()


# TODO fix auto_connect_all
# e.g. see the toggle_disabled tests; they work when explicitly using auto_connect_all=False


class TestGraph:
    def test_add_operation(self, graph, sum_op):
        graph.add_operation(sum_op)
        assert graph.operations == [sum_op]

    def test_add_operations(self, graph, sum_op, square_op):
        operations = [sum_op, square_op]
        graph.add_operations(*operations)
        assert graph.operations == operations

    def test_insert_operation(self, graph, sum_op, square_op):
        graph.insert_operation(0, sum_op)
        graph.insert_operation(0, square_op)
        assert graph.operations == [square_op, sum_op]

    def test_add_link(self, graph, sum_op, square_op):
        graph.add_operation(sum_op)
        graph.add_operation(square_op)
        graph.add_link(source=sum_op, dest=square_op, source_param="sum", dest_param="n")
        sum_inbound_links = graph.get_inbound_links(sum_op)
        sum_outbound_links = graph.get_outbound_links(sum_op)
        square_inbound_links = graph.get_inbound_links(square_op)
        square_outbound_links = graph.get_outbound_links(square_op)
        links = [("sum", "n")]
        assert sum_inbound_links[square_op] == []
        assert sum_outbound_links[square_op] == links
        assert square_inbound_links[sum_op] == links
        assert square_outbound_links[sum_op] == []

    def test_add_multiple_links(self, graph, sum_op, square_op):
        graph.add_operation(sum_op)
        graph.add_operation(square_op)
        import math

        def my_sqrt(num):
            return math.sqrt(num)

        sqrt_op = operation(my_sqrt, output_names=("sqrt"))()
        graph.add_operation(sqrt_op)
        # sum -> square -> sqrt
        #   \               |
        #    -------->------
        graph.add_link(source=sum_op, dest=square_op, source_param="sum", dest_param="n")
        graph.add_link(source=square_op, dest=sqrt_op, source_param="square", dest_param="num")
        graph.add_link(source=sum_op, dest=sqrt_op, source_param="sum", dest_param="num")
        # sum -> square
        assert graph.get_inbound_links(sum_op)[square_op] == []
        assert graph.get_outbound_links(sum_op)[square_op] == [("sum", "n")]
        assert graph.get_inbound_links(square_op)[sum_op] == [("sum", "n")]
        assert graph.get_outbound_links(square_op)[sum_op] == []
        # square -> sqrt
        assert graph.get_inbound_links(square_op)[sqrt_op] == []
        assert graph.get_outbound_links(square_op)[sqrt_op] == [("square", "num")]
        assert graph.get_inbound_links(sqrt_op)[square_op] == [("square", "num")]
        assert graph.get_outbound_links(sqrt_op)[square_op] == []
        # sum -> sqrt
        assert graph.get_inbound_links(sum_op)[sqrt_op] == []
        assert graph.get_outbound_links(sum_op)[sqrt_op] == [("sum", "num")]
        assert graph.get_inbound_links(sqrt_op)[sum_op] == [("sum", "num")]
        assert graph.get_outbound_links(sqrt_op)[sum_op] == []

    def test_add_link_bad_source(self, graph, sum_op):
        with pytest.raises(TypeError):
            graph.add_link("bad", sum_op, "", "")

    def test_add_link_bad_dest(self, graph, sum_op):
        with pytest.raises(TypeError):
            graph.add_link(sum_op, "bad", "", "")

    def test_add_link_missing_source(self, graph, sum_op, square_op):
        graph.add_operation(square_op)
        with pytest.raises(ValueError):
            graph.add_link(sum_op, square_op, "sum", "n")

    def test_add_link_messing_dest(self, graph, sum_op, square_op):
        graph.add_operation(sum_op)
        with pytest.raises(ValueError):
            graph.add_link(sum_op, square_op, "sum", "n")

    def test_add_link_missing_source_param(self, graph, sum_op, square_op):
        with pytest.raises(ValueError):
            graph.add_link(source=sum_op, dest=square_op, source_param="sum", dest_param="dne")

    def test_add_link_missing_dest_param(self, graph, sum_op, square_op):
        with pytest.raises(ValueError):
            graph.add_link(source=sum_op, dest=square_op, source_param="dne", dest_param="n")

    def test_remove_link(self, graph, sum_op, square_op):
        graph.add_operations(sum_op, square_op)
        graph.add_link(sum_op, square_op, source_param="sum", dest_param="n")
        graph.remove_link(sum_op, square_op, "sum", "n")
        assert len(graph.get_inbound_links(sum_op)) == 0 and len(graph.get_inbound_links(square_op)) == 0
        assert len(graph.get_outbound_links(sum_op)) == 0 and len(graph.get_outbound_links(square_op)) == 0

    def test_remove_link_no_links(self, graph, sum_op, square_op):
        graph.add_operations(sum_op, square_op)
        with pytest.raises(ValueError):
            graph.remove_link(sum_op, square_op, "sum", "n")

    def test_get_inbound_links(self, graph, sum_op, square_op):
        graph.add_operations(sum_op, square_op)
        graph.add_link(sum_op, square_op, "sum", "n")
        assert graph.get_inbound_links(sum_op) == {}
        assert graph.get_inbound_links(square_op) == {sum_op: [("sum", "n")]}

    def test_get_inbound_links_empty(self, graph, sum_op):
        assert graph.get_inbound_links(sum_op) == {}

    def test_get_outbound_links(self, graph, sum_op, square_op):
        graph.add_operations(sum_op, square_op)
        graph.add_link(sum_op, square_op, "sum", "n")
        assert graph.get_outbound_links(square_op) == {}
        assert graph.get_outbound_links(sum_op) == {square_op: [("sum", "n")]}

    def test_get_outbound_links_empty(self, graph, sum_op):
        assert graph.get_outbound_links(sum_op) == {}

    def test_clear_operation_links_first(self, graph, sum_op, square_op, negative_op):
        graph.add_operations(sum_op, square_op, negative_op)
        graph.add_link(sum_op, square_op, "sum", "n")
        graph.add_link(square_op, negative_op, "square", "num")
        graph.clear_operation_links(sum_op)
        assert graph.links() == [(square_op, negative_op, "square", "num")]

    def test_clear_operation_links_middle(self, graph, sum_op, square_op, negative_op):
        graph.add_operations(sum_op, square_op, negative_op)
        graph.add_link(sum_op, square_op, "sum", "n")
        graph.add_link(square_op, negative_op, "square", "num")
        graph.clear_operation_links(square_op)
        assert graph.links() == []

    def test_clear_operation_links_end(self, graph, sum_op, square_op, negative_op):
        graph.add_operations(sum_op, square_op, negative_op)
        graph.add_link(sum_op, square_op, "sum", "n")
        graph.add_link(square_op, negative_op, "square", "num")
        graph.clear_operation_links(negative_op)
        assert graph.links() == [(sum_op, square_op, "sum", "n")]

    def test_clear_operation_links_empty(self, graph, sum_op):
        graph.clear_operation_links(sum_op)
        assert graph.links() == []
        assert graph.get_outbound_links(sum_op) == {}
        assert graph.get_inbound_links(sum_op) == {}

    def test_clear_operation_links_bad_arg(self, graph):
        with pytest.raises(TypeError):
            graph.clear_operation_links("this should be an operation")

    def test_clear_operation_links_unlinked_operation(self, graph, sum_op, square_op):
        # TODO should this raise an exception?
        graph.add_operations(sum_op, square_op)
        graph.clear_operation_links(sum_op)
        assert graph.links() == []

    def test_clear_links_empty(self, graph):
        # TODO should this raise an exception
        graph.clear_links()
        assert graph.links() == []

    def test_clear_links(self, graph, sum_op, square_op, negative_op):
        graph.add_operations(sum_op, square_op, negative_op)
        graph.add_link(sum_op, square_op, "sum", "n")
        graph.add_link(square_op, negative_op, "square", "num")
        graph.clear_links()
        assert graph.links() == []

    def test_clear_operations_empty(self, graph):
        graph.clear_operations()
        assert graph.operations == []

    def test_clear_operations(self, graph, sum_op, square_op):
        graph.add_operations(sum_op, square_op)
        graph.clear_operations()
        assert graph.operations == []

    def test_remove_operation_empty(self, graph, sum_op):
        with pytest.raises(ValueError):
            graph.remove_operation(sum_op)

    def test_remove_operation(self, graph, sum_op, square_op):
        graph.add_operations(sum_op, square_op)
        return_value = graph.remove_operation(sum_op)
        assert graph.operations == [square_op]
        assert return_value is None  # no return by default

    def test_remove_operation_linked(self, graph, sum_op, square_op, negative_op):
        graph.add_operations(sum_op, square_op, negative_op)
        graph.add_link(sum_op, square_op, "sum", "n")
        graph.add_link(square_op, negative_op, "square", "num")
        graph.remove_operation(sum_op)
        assert graph.operations == [square_op, negative_op]
        assert graph.links() == [(square_op, negative_op, "square", "num")]

    def test_remove_operation_not_remove_orphan_links(self, graph, sum_op, square_op):
        graph.add_operations(sum_op, square_op)
        to_remove = graph.remove_operation(square_op, remove_orphan_links=False)
        assert graph.operations == [sum_op]
        assert to_remove == (graph.get_inbound_links(square_op), graph.get_outbound_links(square_op))

    def test_remove_operation_bad_arg(self, graph):
        with pytest.raises(TypeError):
            graph.remove_operation("this should be an operation")

    def test_remove_operation_not_in_graph(self, graph, sum_op):
        with pytest.raises(ValueError):
            graph.remove_operation(sum_op)

    def test_as_dask_graph(self, graph, sum_op, square_op, negative_op):
        # Connect sum_op to square_op; don't connect negative_op
        graph.add_operations(sum_op, square_op, negative_op)
        graph.add_link(sum_op, square_op, "sum", "n")
        dask_graph, end_ids = graph.as_dask_graph()

        # Should look like:
        # { "0": (<sum_op>,), "1": (<square_op>, "0"), "2": (<negative_op>,) }
        sum_wrapper = dask_graph["0"]
        square_wrapper = dask_graph["1"]
        negative_wrapper = dask_graph["2"]
        assert len(sum_wrapper) == 1
        assert sum_wrapper[0].node is sum_op
        assert len(square_wrapper) == 2
        assert square_wrapper[0].node is square_op
        assert square_wrapper[1] == "0"
        assert len(negative_wrapper) == 1
        assert negative_wrapper[0].node is negative_op

        # Both square_op and negative_op should be end nodes
        assert sorted(end_ids) == sorted(["1", "2"])

    def test_as_dask_graph_multiple_links(self, graph, sum_op, square_op, negative_op):
        def my_func(x: int, y: int) -> (int, int):
            return y, x

        # Connect sum_op to square_op.
        # Connect sum_op to my_op's x, square_op to my_op's y.
        # Leave negative_op unconnected
        my_op = operation(my_func, output_names=("y", "x"))()
        graph.add_operations(sum_op, square_op, negative_op, my_op)
        graph.add_link(sum_op, square_op, "sum", "n")
        graph.add_link(sum_op, my_op, "sum", "x")
        graph.add_link(square_op, my_op, "square", "y")
        dask_graph, end_ids = graph.as_dask_graph()

        # Should look like:
        sum_wrapper = dask_graph["0"]
        square_wrapper = dask_graph["1"]
        negative_wrapper = dask_graph["2"]
        my_wrapper = dask_graph["3"]

        # sum_op has no dependent nodes (no ops connect into it)
        assert len(sum_wrapper) == 1
        assert sum_wrapper[0].node is sum_op

        # square_op has 1 dependent node, takes sum_op's output
        assert len(square_wrapper) == 2
        assert square_wrapper[0].node is square_op

        # negative_op has no dependent nodes; is unconnected
        assert len(negative_wrapper) == 1
        assert negative_wrapper[0].node is negative_op

        # my_op has two dependent nodes; sum_op and square_op connect to its inputs
        assert len(my_wrapper) == 3
        assert my_wrapper[0].node is my_op
        assert my_wrapper[1] == "0"  # sum_op
        assert my_wrapper[2] == "1"  # square_op

        # negative_op, and my_op should be end nodes
        assert sorted(end_ids) == sorted(["2", "3"])

    def test_as_dask_graph_empty(self, graph):
        # Empty graph, no end nodes
        assert graph.as_dask_graph() == ({}, [])

    def test_as_dask_graph_no_links(self, graph, sum_op):
        graph.add_operation(sum_op)
        dask_graph, end_ids = graph.as_dask_graph()
        assert len(dask_graph["0"]) == 1
        assert dask_graph["0"][0].node is sum_op
        assert end_ids == ["0"]

    def test_operations(self, graph, sum_op):
        graph.add_operation(sum_op)
        assert graph.operations == [sum_op]

    def test_operations_empty(self, graph):
        assert graph.operations == []

    def test_links(self, graph, sum_op, square_op):
        graph.add_operations(sum_op, square_op)
        link = (sum_op, square_op, "sum", "n")
        graph.add_link(*link)
        assert graph.links() == [link]

    def test_links_multiple(self, graph, sum_op):
        def my_func(x: int, y: int) -> (int, int):
            return y, x

        my_op = operation(my_func, output_names=("y", "x"))()
        graph.add_operations(sum_op, my_op)
        link1 = (my_op, sum_op, "y", "n1")
        link2 = (my_op, sum_op, "x", "n2")
        graph.add_link(*link1)
        graph.add_link(*link2)
        assert graph.links() == [link1, link2]

    def test_links_empty(self, graph):
        assert graph.links() == []

    def test_operation_links_bad_arg(self, graph):
        with pytest.raises(TypeError):
            graph.operation_links("this is not an operation")

    def test_operation_links_not_in_graph(self, graph, sum_op):
        with pytest.raises(ValueError):
            graph.operation_links(sum_op)

    def test_operation_links(self, graph, sum_op, square_op):
        graph.add_operations(sum_op, square_op)
        link = (sum_op, square_op, "sum", "n")
        graph.add_link(*link)
        assert graph.operation_links(sum_op) == [link]
        assert graph.operation_links(square_op) == []

    def test_operation_links_multiple(self, sum_op, square_op, negative_op):
        #
        #         (y) --> (n1)
        # my_func           sum (n) --> (num) square
        #         (x) --> (n2)
        #
        def my_func(x: int, y: int) -> (int, int):
            return y, x

        my_op = operation(my_func, output_names=("y", "x"))()
        workflow = Workflow()
        # workflow.add_operations(sum_op, square_op, negative_op, my_op)
        workflow.add_operations(my_op, sum_op, square_op, negative_op)
        link1 = (my_op, sum_op, "y", "n1")
        link2 = (my_op, sum_op, "x", "n2")
        link3 = (sum_op, square_op, "sum", "n")
        link4 = (square_op, negative_op, "square", "num")
        workflow.add_link(my_op, sum_op, "y", "n1")
        workflow.add_link(my_op, sum_op, "x", "n2")
        workflow.add_link(sum_op, square_op, "sum", "n")
        workflow.add_link(square_op, negative_op, "square", "num")
        # assert workflow.operation_links(my_op) == [link1, link2]
        # assert workflow.operation_links(sum_op) == [link3]
        # assert workflow.operation_links(square_op) == [link4]
        # assert workflow.operation_links(negative_op) == []
        workflow._pretty_print()
        dask_graph, end_ids = workflow.as_dask_graph()

        # test execution
        results = workflow.execute_synchronous(x=3, y=5)

    class TestDisable:
        def test_default_no_links(self, graph, sum_op):
            graph.add_operation(sum_op)
            return_value = graph.set_disabled(sum_op)
            assert graph.disabled(sum_op) is True
            assert return_value == []

        def test_default_with_links(self, graph, a_op, b_op, c_op):
            graph = Graph()
            graph.add_operations(a_op, b_op, c_op)
            link_ab = (a_op, b_op, "n", "n")
            link_bc = (b_op, c_op, "n", "n")
            graph.add_link(*link_ab)
            graph.add_link(*link_bc)
            orphan_links = graph.set_disabled(a_op)
            assert graph.disabled(a_op) is True
            assert graph.disabled(b_op) is False
            assert graph.disabled(c_op) is False
            assert graph.links() == [link_bc]
            assert orphan_links == []

        # TODO parameterize these tests
        def test_default_unmatched_names(self, graph, sum_op, square_op, negative_op):
            graph.add_operations(sum_op, square_op, negative_op)
            link1 = (sum_op, square_op, "sum", "n")
            link2 = (square_op, negative_op, "square", "num")
            graph.add_link(*link1)
            graph.add_link(*link2)
            return_value = graph.set_disabled(sum_op)
            assert graph.disabled(sum_op) is True
            assert graph.links() == []
            assert return_value == []

        def test_remove_false(self, graph, a_op, b_op, c_op):
            graph.add_operations(a_op, b_op, c_op)
            link1 = (a_op, b_op, "n", "n")
            link2 = (b_op, c_op, "n", "n")
            graph.add_link(*link1)
            graph.add_link(*link2)
            return_value = graph.set_disabled(a_op, remove_orphan_links=False)
            assert graph.disabled(a_op) is True
            assert graph.links() == [link2]
            assert return_value == [link1]

        def test_remove_false_unmatched_names(self, graph, sum_op, square_op, negative_op):
            graph.add_operations(sum_op, square_op, negative_op)
            link1 = (sum_op, square_op, "sum", "n")
            link2 = (square_op, negative_op, "square", "num")
            graph.add_link(*link1)
            graph.add_link(*link2)
            return_value = graph.set_disabled(sum_op, remove_orphan_links=False)
            assert graph.disabled(sum_op) is True
            assert graph.links() == []
            assert return_value == [link1]

        def test_value_false(self, graph, a_op, b_op, c_op):
            graph.add_operations(a_op, b_op, c_op)
            link1 = (a_op, b_op, "n", "n")
            link2 = (b_op, c_op, "n", "n")
            graph.add_link(*link1)
            graph.add_link(*link2)
            return_value = graph.set_disabled(sum_op, value=False)
            assert graph.disabled(sum_op) is False
            assert graph.links() == [link1, link2]
            assert return_value == []

        def test_value_false_unmatched_names(self, graph, sum_op, square_op, negative_op):
            graph.add_operations(sum_op, square_op, negative_op)
            link1 = (sum_op, square_op, "sum", "n")
            link2 = (square_op, negative_op, "square", "num")
            graph.add_link(*link1)
            graph.add_link(*link2)
            return_value = graph.set_disabled(sum_op, value=False)
            assert graph.disabled(sum_op) is False
            assert graph.links() == []
            assert return_value == []

        def test_value_and_remove_false(self, graph, a_op, b_op, c_op):
            graph.add_operations(a_op, b_op, c_op)
            link1 = (a_op, b_op, "n", "n")
            link2 = (b_op, c_op, "n", "n")
            graph.add_link(*link1)
            graph.add_link(*link2)
            return_value = graph.set_disabled(a_op, value=False, remove_orphan_links=False)
            assert graph.disabled(a_op) is False
            assert graph.links() == [link1, link2]
            assert return_value == []

        def test_value_and_remove_false_unmatched_names(self, graph, sum_op, square_op, negative_op):
            graph.add_operations(sum_op, square_op, negative_op)
            link1 = (sum_op, square_op, "sum", "n")
            link2 = (square_op, negative_op, "square", "num")
            graph.add_link(*link1)
            graph.add_link(*link2)
            return_value = graph.set_disabled(sum_op, value=False, remove_orphan_links=False)
            assert graph.disabled(sum_op) is False
            assert graph.links() == []
            assert return_value == []

        def test_toggle_default(self, graph, sum_op):
            graph.add_operation(sum_op)
            return_value = graph.toggle_disabled(sum_op)
            assert graph.disabled(sum_op) is True
            assert return_value == []
            return_value = graph.toggle_disabled(sum_op)
            assert graph.disabled(sum_op) is False
            assert return_value == []

        def test_toggle_with_links(self, graph, a_op, b_op, c_op):
            graph.add_operations(a_op, b_op, c_op)
            link1 = (a_op, b_op, "n", "n")
            link2 = (b_op, c_op, "n", "n")
            graph.add_link(*link1)
            graph.add_link(*link2)
            return_value = graph.toggle_disabled(a_op)
            assert graph.disabled(a_op) is True
            assert return_value == []
            assert graph.links() == [link2]
            return_value = graph.toggle_disabled(a_op)
            assert graph.disabled(a_op) is False
            assert return_value == []
            assert graph.links() == [link1, link2]

        def test_toggle_with_links_unmatched_names(self, graph, sum_op, square_op, negative_op):
            graph.add_operations(sum_op, square_op, negative_op)
            link1 = (sum_op, square_op, "sum", "n")
            link2 = (square_op, negative_op, "square", "num")
            graph.add_link(*link1)
            graph.add_link(*link2)
            return_value = graph.toggle_disabled(sum_op)
            assert graph.disabled(sum_op) is True
            assert return_value == []
            assert graph.links() == []
            return_value = graph.toggle_disabled(sum_op)
            assert graph.disabled(sum_op) is False
            assert return_value == []
            assert graph.links() == []

        def test_toggle_remove_false(self, graph, a_op, b_op, c_op):
            graph.add_operations(a_op, b_op, c_op)
            link1 = (a_op, b_op, "n", "n")
            link2 = (b_op, c_op, "n", "n")
            graph.add_link(*link1)
            graph.add_link(*link2)
            return_value = graph.toggle_disabled(a_op, remove_orphan_links=False)
            assert graph.disabled(a_op) is True
            assert return_value == [link1]
            assert graph.links() == [link2]
            return_value = graph.toggle_disabled(a_op, remove_orphan_links=False)
            assert graph.disabled(a_op) is False
            assert return_value == []
            assert graph.links() == [link1, link2]

        def test_toggle_remove_false_unmatched_names(self, graph, sum_op, square_op, negative_op):
            graph.add_operations(sum_op, square_op, negative_op)
            link1 = (sum_op, square_op, "sum", "n")
            link2 = (square_op, negative_op, "square", "num")
            graph.add_link(*link1)
            graph.add_link(*link2)
            graph._pretty_print()
            return_value = graph.toggle_disabled(sum_op, remove_orphan_links=False)
            graph._pretty_print()
            assert graph.disabled(sum_op) is True
            assert return_value == [link1]
            assert graph.links() == []
            return_value = graph.toggle_disabled(sum_op, remove_orphan_links=False)
            assert graph.disabled(sum_op) is False
            assert return_value == []
            assert graph.links() == []

    def test_auto_connect_all_only_matching_names(self, graph):
        def my_increment(n: int) -> int:
            return n + 1

        def my_decrement(increment: float) -> float:
            return increment - 1

        increment_op = operation(my_increment, output_names=("increment",))()
        decrement_op = operation(my_decrement, output_names=("end_result",))()
        graph.add_operations(increment_op, decrement_op)
        graph.auto_connect_all()
        assert graph.links() == [(increment_op, decrement_op, "increment", "increment")]

    def test_auto_connect_all_only_matching_types(self, graph):
        def my_increment(n: int) -> int:
            return n + 1

        def my_decrement(m: int) -> int:
            return m - 1

        increment_op = operation(my_increment, output_names=("increment",))()
        decrement_op = operation(my_decrement, output_names=("decrement",))()
        graph.add_operations(increment_op, decrement_op)
        graph.auto_connect_all()
        assert graph.links() == []

    # TODO better test with multiple viable auto links, then prefer the one with matching type as well
    def test_auto_connect_all_matching_names_and_types(self, graph):
        def my_increment(n: int) -> int:
            return n + 1

        def my_decrement(increment: int) -> int:
            return increment - 1

        increment_op = operation(my_increment, output_names=("increment",))()
        decrement_op = operation(my_decrement, output_names=("end_result",))()
        graph.add_operations(increment_op, decrement_op)
        graph.auto_connect_all()
        assert graph.links() == [(increment_op, decrement_op, "increment", "increment")]

    def test_auto_connect_all_none_matching(self, graph, sum_op, square_op, negative_op):
        graph.add_operations(sum_op, square_op, negative_op)
        graph.auto_connect_all()
        assert graph.links() == []


class TestWorkflow:
    # TODO: test callback_slot
    # TODO: test finished_slot
    # TODO: test except_slot
    # TODO: test execute_all

    def test_execute_no_operations(self):
        workflow = Workflow("Test Workflow")
        results = workflow.execute().result()
        assert results == ({},)

    def test_execute_operation_no_default_no_value(self, sum_op):
        # not sure how to test this....
        def handle_exception(exception):
            with pytest.raises(TypeError):
                raise exception

        workflow = Workflow()
        workflow.add_operation(sum_op)
        results = workflow.execute(except_slot=handle_exception).result()
        print(results)

    def test_execute_operation_no_default(self, sum_op):
        workflow = Workflow()
        workflow.add_operation(sum_op)
        results = workflow.execute(n1=10, n2=5).result()
        assert results == ({"sum": 15},)

    def test_execute_operation_default_input_value(self):
        @operation
        @output_names("doubled")
        def double(x=10):
            return x * 2

        workflow = Workflow()
        double_op = double()
        workflow.add_operation(double_op)
        results = workflow.execute().result()
        assert results == ({"doubled": 20},)

    def test_execute_no_links_diff_input_names(self, sum_op, square_op, negative_op):
        # do the input names have to match in this case (more than one entry op)
        operations = [sum_op, square_op, negative_op]
        workflow = Workflow(name="test", operations=operations)
        results = workflow.execute(n1=3, n2=-3, n=10, num=33).result()
        assert len(results) == 3
        assert {"sum": 0} in results
        assert {"square": 100} in results
        assert {"negative": -33} in results

    def test_execute_no_links_same_input_name(self):
        @operation
        @output_names("doubled")
        def double(n):
            return n * 2

        @operation
        @output_names("tripled")
        def triple(n):
            return n * 3

        workflow = Workflow()
        double_op = double()
        triple_op = triple()
        workflow.add_operations(double_op, triple_op)
        results = workflow.execute(n=10).result()
        assert len(results) == 2
        assert {"doubled": 20} in results
        assert {"tripled": 30} in results

    def test_execute(self, sum_op, square_op, negative_op):
        workflow = Workflow()
        workflow.add_operations(sum_op, square_op, negative_op)
        workflow.add_link(sum_op, square_op, "sum", "n")
        workflow.add_link(square_op, negative_op, "square", "num")
        results = workflow.execute(n1=2, n2=5).result()
        assert results == ({"negative": -49},)

    def test_execute_synchronous(self, sum_op, square_op, negative_op):
        workflow = Workflow()
        workflow.add_operations(sum_op, square_op, negative_op)
        workflow.add_link(sum_op, square_op, "sum", "n")
        workflow.add_link(square_op, negative_op, "square", "num")
        results = workflow.execute_synchronous(n1=2, n2=5)
        assert results == ({"negative": -49},)

    def test_execute_synchronous_no_links_not_enough_kwargs(self, sum_op, square_op, negative_op):
        workflow = Workflow()
        workflow.add_operations(sum_op, square_op, negative_op)
        with pytest.raises(TypeError):
            results = workflow.execute_synchronous(n1=2, n2=5)

    def test_execute_synchronous_no_links(self, sum_op, square_op, negative_op):
        workflow = Workflow()
        workflow.add_operations(sum_op, square_op, negative_op)
        # n1, n2 -- inputs to sum_op;
        # n -- input to square_op
        # num -- input to negative_op
        results = workflow.execute_synchronous(n1=2, n2=5, n=10, num=50)
        assert len(results) == 3
        assert {"sum": 7} in results
        assert {"square": 100} in results
        assert {"negative": -50} in results

    def test_execute_all(self, qtbot, sum_op, square_op, negative_op):
        results = [{"negative": (1 + 2) ** 2 * -1},
                   {"negative": (3 + 4) ** 2 * -1},
                   {"negative": (5 + 6) ** 2 * -1}]
        def cb(*result):
            next_result = results.pop(0)
            assert result == next_result
        workflow = Workflow()
        workflow.add_operations(sum_op, square_op, negative_op)
        workflow.add_link(sum_op, square_op, "sum", "n")
        workflow.add_link(square_op, negative_op, "square", "num")
        n1_values = [1, 3, 5]
        n2_values = [2, 4, 6]
        # TODO -- we are only getting one result, should get three (3 pairs of n1/n2).
        workflow.execute_all(callback_slot=cb, n1=n1_values, n2=n2_values).result()

    def test_fill_kwargs(self):
        assert False

    def test_validate(self):
        assert False

    def test_notify_no_observers(self):
        workflow = Workflow()
        workflow.notify()

    def test_notify(self):
        self.flag = False

        def observer():
            self.flag = not self.flag

        workflow = Workflow()
        workflow.attach(observer)
        workflow.notify()
        assert self.flag is True


class TestMultipleOutputsOneOp:
    # Tests when a tuple is returned representing multiple outputs (in this case, 2)
    #   tests when all outputs are named: return a1, a2 -> 'x', 'y'
    #   tests when output tuple is named: return a1, a2 -> 'return_val'
    #   tests when not using @output_names
    def test_all_output_names(self):
        @operation
        @output_names('x', 'y')
        def my_func(a1, a2):
            return a1, a2

        op = my_func()
        workflow = Workflow()
        workflow.add_operations(op)
        result = workflow.execute_synchronous(a1=1, a2=2)
        print(result)
        assert result == ({'x': 1, 'y': 2},)

    def test_one_output_name(self):
        @operation
        @output_names("return_val")
        def my_func(a1, a2):
            return a1, a2

        op = my_func()
        workflow = Workflow()
        workflow.add_operations(op)
        result = workflow.execute_synchronous(a1=1, a2=2)
        assert result == ({"return_val": 1},)

    def test_no_output_names(self):
        @operation
        def my_func(a1, a2):
            return a1, a2

        op = my_func()
        w = Workflow()
        w.add_operations(op)
        result = w.execute_synchronous(a1=1, a2=2)
        assert result == ({"my_func": 1},)


class TestMultipleOutputsMultipleOps:
    # TEST CASES
    #   two nodes connect into one node with two inputs
    #   start node has return x, y
    #   middle node has return x, y
    #   end node has return x, y
    def test_two_copy_ops_to_one_op(self, double_and_triple_op, sum_op, square_op):
        # 1**2 + 2**2 => 5
        workflow = Workflow()
        square_op.filled_values.update(n=1)
        square_op_2 = square_op.__class__()
        square_op_2.filled_values.update(n=2)
        square_op_2.output_names = ["square"]
        workflow.add_operations(sum_op, square_op, square_op_2)
        workflow.add_link(square_op, sum_op, "square", "n1")
        workflow.add_link(square_op_2, sum_op, "square", "n2")
        workflow._pretty_print()
        result = workflow.execute_synchronous()
        assert result == ({"sum": 5},)

    def test_two_ops_to_one_op(self, negative_op, square_op, sum_op):
        workflow = Workflow()
        workflow.add_operations(negative_op, square_op, sum_op)
        workflow.add_link(negative_op, sum_op, "negative", "n1")
        workflow.add_link(square_op, sum_op, "square", "n2")
        print(workflow.get_inbound_links(sum_op))
        #from dask import visualize
        #visualize(workflow.as_dask_graph()[0], filename="/home/ihumphrey/graph")
        graph = workflow.as_dask_graph()[0]
        print(graph)
        for k, op in graph.items():
            print(k, op[0].node.name)
        from dask.threaded import get
        negative_op.filled_values.update(num=3)
        square_op.filled_values.update(n=4)
        print(get(graph, '0'))  # WHY is this an issue? Complains that sum missing required 'n2'
        # workflow._pretty_print()
        # result = workflow.execute_synchronous(num=3, n=4)
        # assert result == ({"sum": 13},)

    def test_start_node(self, double_and_triple_op, sum_op, square_op):
        workflow = Workflow()
        workflow.add_operations(double_and_triple_op, sum_op, square_op)
        workflow.add_link(double_and_triple_op, sum_op, "double", "n1")
        workflow.add_link(double_and_triple_op, sum_op, "triple", "n2")
        workflow.add_link(sum_op, square_op, "sum", "n")
        result = workflow.execute_synchronous(n=1)
        assert result == ({"square": 25},)

    def test_middle_node(self, double_and_triple_op, sum_op, square_op):
        workflow = Workflow()
        workflow.add_operations(double_and_triple_op, sum_op, square_op)
        workflow.add_link(sum_op, double_and_triple_op, "sum", "n")
        workflow.add_link(double_and_triple_op, square_op, "triple", "n")
        result = workflow.execute_synchronous(n1=1, n2=2)
        assert result == ({"square": 81},)

    def test_end_node(self, double_and_triple_op, sum_op, square_op):
        workflow = Workflow()
        workflow.add_operations(double_and_triple_op, sum_op, square_op)
        workflow.add_link(sum_op, square_op, "sum", "n")
        workflow.add_link(square_op, double_and_triple_op, "square", "n")
        result = workflow.execute_synchronous(n1=1, n2=2)
        assert result == ({"double": 18, "triple": 27},)

    # TODO: should this be allowed?
    # def test_same_connection_multiple_inputs(self, double_and_triple_op, sum_op, square_op):
    #     workflow = Workflow()
    #     workflow.add_operations(sum_op, square_op)
    #     workflow.add_link(square_op, sum_op, "square", "n1")
    #     workflow.add_link(square_op, sum_op, "square", "n2")
    #     workflow._pretty_print()
    #
    #     result = workflow.execute_synchronous(n=3)
    #     assert result == ({"sum": 18},)


def test_mutliple_end_nodes(double_and_triple_op, sum_op, square_op):
    workflow = Workflow()
    workflow.add_operations(double_and_triple_op, sum_op, square_op)
    workflow.add_link(sum_op, double_and_triple_op, "sum", "n")
    workflow.add_link(sum_op, square_op, "sum", "n")
    result = workflow.execute_synchronous(n1=2, n2=3)
    assert len(result) == 2
    assert {"double": 10, "triple": 15} in result
    assert {"square": 25} in result


def test_copy(simple_workflow:Workflow):
    f = io.StringIO()
    with contextlib.redirect_stdout(f):
        simple_workflow._pretty_print()
    original = f.getvalue()

    clone = simple_workflow.clone()

    f = io.StringIO()
    with contextlib.redirect_stdout(f):
        clone._pretty_print()
    new = f.getvalue()

    assert original == new

    result1 = simple_workflow.execute_synchronous(n=2)
    result2 = clone.execute_synchronous(n=2)

    assert result1 == result2
