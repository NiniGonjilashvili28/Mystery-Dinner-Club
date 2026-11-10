"""Tests for the HTTP endpoints, through Flask's test client."""
from conftest import needs_db

pytestmark = needs_db


def test_health_is_ok(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.get_json()["status"] == "ok"


def test_cities_lists_ten_cities(client):
    assert len(client.get("/cities").get_json()["cities"]) == 10


def test_match_returns_a_restaurant_id(client):
    response = client.post("/matches", json={"city": "Madrid", "theme_choice": "random",
                                             "budget": 50, "exclude_ids": []})
    assert response.status_code == 200
    assert isinstance(response.get_json()["restaurant_id"], int)


def test_match_returns_404_when_nothing_fits(client):
    response = client.post("/matches", json={"city": "Madrid", "theme_choice": "luxury",
                                             "budget": 30, "exclude_ids": []})
    assert response.status_code == 404


def test_match_rejects_a_bad_request(client):
    assert client.post("/matches", json={"city": "Madrid"}).status_code == 400


def test_restaurant_details_and_404(client):
    assert client.get("/restaurants/1").status_code == 200
    assert client.get("/restaurants/99999").status_code == 404


def test_cors_allows_only_the_ui_origin(client):
    allowed = client.get("/cities", headers={"Origin": "http://ui.test"})
    other = client.get("/cities", headers={"Origin": "http://evil.test"})
    assert allowed.headers["Access-Control-Allow-Origin"] == "http://ui.test"
    assert "Access-Control-Allow-Origin" not in other.headers