import pytest
from xicam.gui.models.treemodel import Tree


@pytest.fixture(scope='function')
def tree() -> Tree:
    # parent_a
    #  - child_a_1
    #    - grandchild_a_1_1
    # parent_b
    #  - child_b_1
    #    - grandchild_b_1_1
    #    - grandchild_b_1_2
    #  - child_b_2
    # parent3
    tree = Tree()
    parent_a = "parent a"
    parent_b = "parent b"
    parent_c = "parent c"
    tree.add_node(parent_a)
    tree.add_node(parent_b)
    tree.add_node(parent_c)

    child_a_1 = "child a 1"
    child_b_1 = "child b 1"
    child_b_2 = "child b 2"
    tree.add_node(child_a_1, parent=parent_a)
    tree.add_node(child_b_1, parent=parent_b)
    tree.add_node(child_b_2, parent=parent_b)

    grandchild_a_1_1 = "grandchild a 1 1"
    grandchild_b_1_1 = "grandchild b 1 1"
    grandchild_b_1_2 = "grandchild b 1 2"
    tree.add_node(grandchild_a_1_1, parent=child_a_1)
    tree.add_node(grandchild_b_1_1, parent=child_b_1)
    tree.add_node(grandchild_b_1_2, parent=child_b_1)

    # tree.add_node(parent_c)  # TODO: test when duplicate obj added (shouldn't be allowed???)
    return tree


class TestTree:

    def test___contains__(self, tree):
        assert not "DNE" in tree

        assert "child a 1" in tree

        assert "grandchild b 1 2" in tree

    def test_add_node(self, tree):
        tree.add_node("new parent")
        assert "new parent" in tree

        tree.add_node("new child")
        assert "new child" in tree

    def test_children(self, tree):
        assert "child a 1" in tree.children("parent a")
        assert "child b 2" in tree.children("parent b")
        assert len(tree.children("parent c")) == 0
        with pytest.raises(KeyError):
            assert len(tree.children("DNE"))

    def test_child_count(self, tree: Tree):
        assert tree.child_count("child b 1") == 2
        assert tree.child_count(None) == 3

    def test_has_children(self, tree: Tree):
        assert tree.has_children("child b 1")
        assert tree.has_children(None)

    def test_index(self, tree: Tree):
        assert tree.index("parent a") == (0, None)
        assert tree.index("parent b") == (1, None)  # TODO: why isn't this in order (thinks parent b @ index 2)?
        assert tree.index("child a 1") == (0, "parent a")
        assert tree.index("grandchild b 1 2") == (1, "child b 1")

    def test_insert_node(self, tree: Tree):
        child_count = tree.child_count(None)
        tree.insert_node('new node', 0, None)
        assert tree.children(None)[0] == 'new node'
        assert tree.child_count(None) == child_count + 1

    def test_node(self, tree: Tree):
        assert tree.node(0, None) == "parent a"
        assert tree.node(0, "parent a") == 'child a 1'

    def test_parent(self, tree: Tree):
        assert tree.parent("parent a") == None
        assert tree.parent("child a 1") == "parent a"

    def test_remove_children_dont_drop(self, tree):
        with pytest.raises(RuntimeError):
            tree.remove_children("parent a", drop_grandchildren=False)
        assert "parent a" in tree

    def test_remove_children(self, tree):
        tree.remove_children("parent a")
        assert "parent a" in tree
        assert "child a 1" not in tree and "grandchild a 1 1" not in tree
        assert "parent b" in tree and "parent c" in tree

    def test_remove_node_child(self, tree):
        tree.remove_node("grandchild a 1 1")
        assert "grandchild a 1 1" not in tree
        assert "parent a" in tree and "child a 1" in tree

    def test_remove_node_not_in_tree(self, tree):
        with pytest.raises(KeyError):
            tree.remove_node("DNE")

    def test_remove_node_dont_drop_children(self, tree):
        with pytest.raises(RuntimeError):
            tree.remove_node("parent a", drop_children=False)

        assert "parent a" in tree

    def test_remove_node_parent(self, tree):
        tree.remove_node("parent a")
        assert "parent a" not in tree
        assert "child a 1" not in tree
        assert "grandchild a 1 1" not in tree
        assert "parent b" in tree and "parent c" in tree

    def test_duplicate(self, tree: Tree):
        with pytest.raises(ValueError):
            tree.add_node("parent a", None)
