from ..conftest import login


def test_staff_home_lists_their_rooms(client, school):
    login(client, school.amy)
    page = client.get("/").data
    assert b"Saplings" in page and b"Oaks" not in page


def test_parent_home_lists_their_children(client, school):
    login(client, school.sam)
    page = client.get("/").data
    assert b"Ava Reid" in page and b"Kit" not in page


def test_parent_without_children_is_told_so(client, school):
    from school_portal.models import Role

    from ..conftest import make_user

    login(client, make_user(Role.PARENT))
    assert b"not linked to a child" in client.get("/").data
