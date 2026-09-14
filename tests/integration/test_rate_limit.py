from school_portal.models import Role

from ..conftest import PASSWORD, make_user


def test_too_many_failures_block_the_address(client, app):
    user = make_user(Role.PARENT, email="sam@example.com")
    for _ in range(5):
        assert (
            client.post("/login", data={"email": user.email, "password": "wrong"}).status_code
            == 401
        )
    # Even the right password is refused while blocked.
    response = client.post("/login", data={"email": user.email, "password": PASSWORD})
    assert response.status_code == 429


def test_a_success_clears_earlier_failures(client, app):
    user = make_user(Role.PARENT, email="sam@example.com")
    for _ in range(4):
        client.post("/login", data={"email": user.email, "password": "wrong"})
    assert (
        client.post("/login", data={"email": user.email, "password": PASSWORD}).status_code == 302
    )
    client.post("/logout")
    for _ in range(4):
        client.post("/login", data={"email": user.email, "password": "wrong"})
    assert (
        client.post("/login", data={"email": user.email, "password": PASSWORD}).status_code == 302
    )


def test_one_client_trying_many_addresses_is_blocked(client, app):
    user = make_user(Role.PARENT, email="sam@example.com")
    for n in range(20):
        client.post("/login", data={"email": f"guess{n}@example.com", "password": "x"})
    response = client.post("/login", data={"email": user.email, "password": PASSWORD})
    assert response.status_code == 429


def test_old_attempts_are_pruned(app):
    from datetime import timedelta

    from school_portal import ratelimit, timeutil
    from school_portal.extensions import db
    from school_portal.models import LoginAttempt

    db.session.add(LoginAttempt(email="a", ip="b", at=timeutil.now() - timedelta(days=8)))
    db.session.add(LoginAttempt(email="a", ip="b"))
    db.session.commit()
    assert ratelimit.prune() == 1
