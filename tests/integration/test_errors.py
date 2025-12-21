from ..conftest import login, make_user


def test_not_found_page(client, app):
    login(client, make_user("staff"))
    response = client.get("/no/such/page")
    assert response.status_code == 404
    assert b"There is nothing at this address" in response.data


def test_htmx_requests_get_a_short_answer(client, app):
    login(client, make_user("staff"))
    response = client.get("/no/such/page", headers={"HX-Request": "true"})
    assert response.status_code == 404
    assert response.data == b"Not found"
