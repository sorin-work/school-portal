def test_health_reports_the_database(client):
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json == {"status": "ok", "database": "ok"}
