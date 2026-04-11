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


def test_reports_waiting_for_a_parent_show_on_both_homes(client, school):
    from school_portal import timeutil
    from school_portal.extensions import db
    from school_portal.models import Event

    db.session.add(
        Event(
            child_id=school.ava.id,
            room_id=school.saplings.id,
            kind="accident",
            occurred_at=timeutil.now(),
            details={},
            note="Bump",
            needs_ack=True,
        )
    )
    db.session.commit()
    login(client, school.amy)
    assert b"Waiting for a parent" in client.get("/").data
    client.post("/logout")
    login(client, school.sam)
    assert b"Please read and acknowledge" in client.get("/").data
