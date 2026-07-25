from datetime import timedelta

from sqlalchemy import select

from school_portal import timeutil
from school_portal.extensions import db
from school_portal.models import Rsvp, SchoolEvent

from ..conftest import link, login, make_user


def make_trip(school, **fields):
    day = timeutil.today() + timedelta(days=10)
    login_client = fields.pop("client")
    login(login_client, school.admin)
    data = {
        "title": "Farm trip",
        "kind": "trip",
        "day": day.isoformat(),
        "start": "09:30",
        "end": "14:00",
        "rooms": [str(school.saplings.id)],
        "consent_required": "y",
        "consent_text": "I agree to the coach trip.",
        "respond_by": (day - timedelta(days=2)).isoformat(),
    }
    data.update(fields)
    response = login_client.post("/calendar/new", data=data)
    assert response.status_code == 302, response.data
    login_client.post("/logout")
    return db.session.scalar(select(SchoolEvent))


def test_families_of_the_room_see_the_trip(client, school):
    trip = make_trip(school, client=client)
    assert trip.consent_required and trip.rsvp_required
    login(client, school.sam)
    assert b"Farm trip" in client.get("/calendar/").data
    client.post("/logout")
    login(client, school.pat)
    assert b"Farm trip" not in client.get("/calendar/").data
    assert client.get(f"/calendar/{trip.id}").status_code == 404


def test_consent_needs_the_box_and_a_name(client, school):
    trip = make_trip(school, client=client)
    login(client, school.sam)
    url = f"/calendar/{trip.id}/children/{school.ava.id}/reply"
    client.post(url, data={"attending": "yes"})
    assert db.session.scalar(select(Rsvp)) is None
    client.post(url, data={"attending": "yes", "consent": "yes", "signed_name": "Sam Reid"})
    rsvp = db.session.scalar(select(Rsvp))
    assert rsvp.attending and rsvp.consent_given and rsvp.signed_name == "Sam Reid"
    client.post(url, data={"attending": "no"})
    db.session.refresh(rsvp)
    assert not rsvp.attending and not rsvp.consent_given


def test_children_outside_the_audience_cannot_reply(client, school):
    trip = make_trip(school, client=client)
    login(client, school.pat)
    response = client.post(
        f"/calendar/{trip.id}/children/{school.kit.id}/reply", data={"attending": "no"}
    )
    assert response.status_code == 404


def test_read_only_guardians_cannot_sign(client, school):
    trip = make_trip(school, client=client)
    gran = make_user("parent", email="gran@example.com")
    link(gran, school.ava, access="read_only")
    login(client, gran)
    response = client.post(
        f"/calendar/{trip.id}/children/{school.ava.id}/reply",
        data={"attending": "yes", "consent": "yes", "signed_name": "Gran"},
    )
    assert response.status_code == 404


def test_replies_close(client, school):
    trip = make_trip(school, client=client)
    trip.respond_by = timeutil.today() - timedelta(days=1)
    db.session.commit()
    login(client, school.sam)
    client.post(
        f"/calendar/{trip.id}/children/{school.ava.id}/reply",
        data={"attending": "yes", "consent": "yes", "signed_name": "Sam"},
    )
    assert db.session.scalar(select(Rsvp)) is None


def test_staff_download_the_replies(client, school):
    trip = make_trip(school, client=client)
    db.session.add(
        Rsvp(
            school_event_id=trip.id,
            child_id=school.ava.id,
            attending=True,
            consent_given=True,
            signed_name='=HYPERLINK("http://x")',
        )
    )
    db.session.commit()
    login(client, school.amy)
    response = client.get(f"/calendar/{trip.id}/replies.csv")
    assert response.mimetype == "text/csv"
    text = response.data.decode()
    assert "Ava Reid" in text and "Leon Kowalczyk" in text
    assert "'=HYPERLINK" in text
    client.post("/logout")
    login(client, school.sam)
    assert client.get(f"/calendar/{trip.id}/replies.csv").status_code == 403


def test_a_closure_for_everyone(client, school):
    login(client, school.admin)
    client.post(
        "/calendar/new",
        data={
            "title": "Staff training day",
            "kind": "closure",
            "day": (timeutil.today() + timedelta(days=3)).isoformat(),
            "all_day": "y",
        },
    )
    client.post("/logout")
    login(client, school.pat)
    assert b"Staff training day" in client.get("/calendar/").data
