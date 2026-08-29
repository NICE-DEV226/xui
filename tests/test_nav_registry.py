from xui.nav import NavNode, NavRegistry


def test_register_and_tree_basic():
    reg = NavRegistry()
    reg.register(NavNode(id="a", label="A", plugin="p1", path="/a"))
    reg.register(NavNode(id="b", label="B", plugin="p1", path="/b", parent_id="a"))

    tree = reg.tree()
    assert len(tree) == 1
    assert tree[0]["id"] == "a"
    assert tree[0]["children"][0]["id"] == "b"


def test_duplicate_id_raises():
    reg = NavRegistry()
    reg.register(NavNode(id="a", label="A", plugin="p1"))
    try:
        reg.register(NavNode(id="a", label="A2", plugin="p2"))
        assert False, "expected ValueError"
    except ValueError as exc:
        assert "p1" in str(exc)


def test_permission_filtering():
    reg = NavRegistry()
    reg.register(NavNode(id="a", label="A", plugin="p1", permission="admin"))
    reg.register(NavNode(id="b", label="B", plugin="p1"))

    assert [n["id"] for n in reg.tree(user_roles=set())] == ["b"]
    assert {n["id"] for n in reg.tree(user_roles={"admin"})} == {"a", "b"}
    assert {n["id"] for n in reg.tree(user_roles=None)} == {"a", "b"}


def test_unregister_plugin_removes_its_nodes():
    reg = NavRegistry()
    reg.register(NavNode(id="a", label="A", plugin="p1"))
    reg.register(NavNode(id="b", label="B", plugin="p2"))

    reg.unregister_plugin("p1")

    assert [n["id"] for n in reg.tree()] == ["b"]


def test_orphan_parent_id_treated_as_root():
    reg = NavRegistry()
    reg.register(NavNode(id="a", label="A", plugin="p1", parent_id="ghost"))

    tree = reg.tree()
    assert [n["id"] for n in tree] == ["a"]


def test_ordering_by_order_then_label():
    reg = NavRegistry()
    reg.register(NavNode(id="z", label="Zeta", plugin="p1", order=1))
    reg.register(NavNode(id="a", label="Alpha", plugin="p1", order=1))
    reg.register(NavNode(id="m", label="Mid", plugin="p1", order=0))

    assert [n["id"] for n in reg.tree()] == ["m", "a", "z"]
