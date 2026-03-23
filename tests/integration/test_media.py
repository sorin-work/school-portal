import io

from sqlalchemy import select

from school_portal.extensions import db
from school_portal.models import Event, Media

from ..conftest import login
from ..images import jpeg_with_exif


def observe(client, room, children, *files, visibility="parents"):
    return client.post(
        f"/rooms/{room.id}/observe",
        data={
            "child_ids": [str(c.id) for c in children],
            "note": "Building a tower",
            "visibility": visibility,
            "photos": [(io.BytesIO(data), name) for name, data in files],
        },
        content_type="multipart/form-data",
    )


def consent(*children, value="group"):
    """Give the children photo consent, once consent exists."""
    for child in children:
        child.photo_consent = value
    db.session.commit()


def only_media():
    (media,) = db.session.scalars(select(Media))
    return media


def test_a_photo_is_stored_without_exif_and_served_to_staff(client, school):
    consent(school.ava)
    login(client, school.amy)
    response = observe(client, school.saplings, [school.ava], ("tower.jpg", jpeg_with_exif()))
    assert response.status_code == 302
    media = only_media()
    response = client.get(f"/media/{media.id}")
    assert response.status_code == 200
    assert response.mimetype == "image/jpeg"
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert b"Example Camera Co" not in response.data
    assert client.get(f"/media/{media.id}/thumb").status_code == 200


def test_files_that_are_not_images_are_refused(client, school):
    consent(school.ava)
    login(client, school.amy)
    response = observe(client, school.saplings, [school.ava], ("notes.jpg", b"<html>not a photo"))
    assert response.status_code == 200
    assert b"not an image" in response.data
    assert db.session.scalars(select(Media)).all() == []
    assert db.session.scalars(select(Event)).all() == []


def test_parents_of_the_child_see_the_photo_and_others_do_not(client, school):
    consent(school.ava)
    login(client, school.amy)
    observe(client, school.saplings, [school.ava], ("tower.jpg", jpeg_with_exif()))
    media = only_media()
    client.post("/logout")
    login(client, school.sam)
    assert client.get(f"/media/{media.id}").status_code == 200
    client.post("/logout")
    login(client, school.pat)
    assert client.get(f"/media/{media.id}").status_code == 404
    client.post("/logout")
    login(client, school.ben)
    assert client.get(f"/media/{media.id}").status_code == 404


def test_photos_of_staff_only_events_stay_with_staff(client, school):
    consent(school.ava)
    login(client, school.amy)
    observe(
        client, school.saplings, [school.ava], ("tower.jpg", jpeg_with_exif()), visibility="staff"
    )
    media = only_media()
    client.post("/logout")
    login(client, school.sam)
    assert client.get(f"/media/{media.id}").status_code == 404


def test_signed_out_users_get_nothing(client, school):
    consent(school.ava)
    login(client, school.amy)
    observe(client, school.saplings, [school.ava], ("tower.jpg", jpeg_with_exif()))
    media = only_media()
    client.post("/logout")
    assert client.get(f"/media/{media.id}").status_code == 302


def test_group_photo_needs_the_other_childs_group_consent(client, school):
    from ..conftest import link, make_user

    leon_parent = make_user("parent", email="leonparent@example.com")
    link(leon_parent, school.leon)
    consent(school.ava, value="group")
    consent(school.leon, value="own")
    login(client, school.amy)
    observe(client, school.saplings, [school.ava, school.leon], ("pair.jpg", jpeg_with_exif()))
    media = only_media()
    client.post("/logout")
    # Leon's consent is "own", so Ava's family may not see a photo with him in it.
    login(client, school.sam)
    assert client.get(f"/media/{media.id}").status_code == 404
    assert b"/media/" not in client.get(f"/children/{school.ava.id}/diary").data
    client.post("/logout")
    # Ava allows group photos, so Leon's family may.
    login(client, leon_parent)
    assert client.get(f"/media/{media.id}").status_code == 200
    client.post("/logout")
    consent(school.leon, value="group")
    login(client, school.sam)
    assert client.get(f"/media/{media.id}").status_code == 200


def test_photos_are_refused_for_a_child_without_consent(client, school):
    consent(school.ava, value="none")
    login(client, school.amy)
    response = observe(client, school.saplings, [school.ava], ("tower.jpg", jpeg_with_exif()))
    assert b"No photo consent for Ava R." in response.data
    assert db.session.scalars(select(Media)).all() == []
