"""A parent sees their own children and nobody else's; staff see their rooms.

Every route that takes a child id is tried with a child outside the user's
scope, and must answer 404 (never 403, so ids cannot be probed).
"""

import pytest

from school_portal import access
from school_portal.extensions import db
from school_portal.models import Role

from ..conftest import link, login, make_child, make_user


def test_parent_children_query_holds_only_their_children(school):
    names = [c.first_name for c in db.session.scalars(access.children_query(school.sam))]
    assert names == ["Ava"]


def test_staff_see_the_rooms_they_work_in(school):
    names = {c.first_name for c in db.session.scalars(access.children_query(school.amy))}
    assert names == {"Ava", "Leon"}
    names = {c.first_name for c in db.session.scalars(access.children_query(school.ben))}
    assert names == {"Kit"}


def test_administrators_see_everyone(school):
    names = {c.first_name for c in db.session.scalars(access.children_query(school.admin))}
    assert names == {"Ava", "Leon", "Kit"}


def test_no_access_links_see_nothing(school):
    excluded = make_user(Role.PARENT, email="excluded@example.com")
    link(excluded, school.ava, access="none")
    assert list(db.session.scalars(access.children_query(excluded))) == []
    assert not access.can_view_child(excluded, school.ava)


def test_read_only_links_see_but_do_not_act(school):
    gran = make_user(Role.PARENT, email="gran@example.com")
    link(gran, school.ava, access="read_only")
    assert access.can_view_child(gran, school.ava)
    assert not access.can_act_for_child(gran, school.ava)


OTHER_CHILD_URLS = []


@pytest.mark.parametrize("template", OTHER_CHILD_URLS)
def test_parent_gets_404_for_another_child(client, school, template):
    login(client, school.sam)
    assert client.get(template.format(id=school.ava.id)).status_code == 200
    assert client.get(template.format(id=school.kit.id)).status_code == 404
    assert client.get(template.format(id=999999)).status_code == 404


@pytest.mark.parametrize("template", OTHER_CHILD_URLS)
def test_staff_get_404_outside_their_rooms(client, school, template):
    if template.endswith("/absence"):
        pytest.skip("staff record absences from the register")
    login(client, school.amy)
    assert client.get(template.format(id=school.leon.id)).status_code == 200
    assert client.get(template.format(id=school.kit.id)).status_code == 404


def test_excluded_guardian_gets_404(client, school):
    excluded = make_user(Role.PARENT, email="excluded@example.com")
    link(excluded, school.ava, access="none")
    login(client, excluded)
    for template in OTHER_CHILD_URLS:
        assert client.get(template.format(id=school.ava.id)).status_code == 404


def test_parents_cannot_open_staff_pages(client, school):
    login(client, school.sam)
    assert client.get("/admin/children/").status_code == 403


def test_medical_notes_are_staff_only_by_default(client, school):
    school.ava.medical_notes = "Inhaler in the office"
    db.session.commit()
    login(client, school.sam)
    assert not access.can_see_medical(school.sam, school.ava)
    assert access.can_see_medical(school.amy, school.ava)
    school.ava.share_medical_with_parents = True
    db.session.commit()
    assert access.can_see_medical(school.sam, school.ava)


def test_children_without_a_room_are_seen_only_by_admins(school):
    lone = make_child(None, "Lone")
    assert lone.id in {c.id for c in db.session.scalars(access.children_query(school.admin))}
    assert lone.id not in {c.id for c in db.session.scalars(access.children_query(school.amy))}
