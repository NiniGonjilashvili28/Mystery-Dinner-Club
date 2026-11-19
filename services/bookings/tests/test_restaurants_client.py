"""Tests for the HTTP calls to the Restaurants service, with a fake network."""
import pytest
import requests

from restaurants_client import RestaurantsClient, RestaurantsUnavailable


class FakeResponse:
    def __init__(self, status_code, body=None):
        self.status_code = status_code
        self.body = body

    def json(self):
        return self.body


class FakeSession:
    """Stands in for requests.Session: returns a prepared answer, or raises an error."""

    def __init__(self, response=None, error=None):
        self.response = response
        self.error = error
        self.calls = []

    def request(self, method, url, json=None, timeout=None):
        self.calls.append((method, url, json, timeout))
        if self.error:
            raise self.error
        return self.response


def client_with(response=None, error=None):
    session = FakeSession(response, error)
    return RestaurantsClient("http://restaurants:8000/", timeout_s=2, session=session), session


def test_list_cities_returns_the_names():
    client, session = client_with(FakeResponse(200, {"cities": [{"city": "Madrid"}, {"city": "Rome"}]}))
    assert client.list_cities() == ["Madrid", "Rome"]
    assert session.calls[0][:2] == ("GET", "http://restaurants:8000/cities")


def test_every_call_has_the_timeout():
    client, session = client_with(FakeResponse(200, {"cities": []}))
    client.list_cities()
    assert session.calls[0][3] == 2


def test_find_match_sends_the_request_and_returns_the_id():
    client, session = client_with(FakeResponse(200, {"restaurant_id": 23}))
    assert client.find_match("Madrid", "bar", 50, [4, 5]) == 23
    assert session.calls[0][2] == {"city": "Madrid", "theme_choice": "bar", "budget": 50, "exclude_ids": [4, 5]}


def test_find_match_returns_none_when_nothing_fits():
    client, _ = client_with(FakeResponse(404, {"error": "no_match"}))
    assert client.find_match("Madrid", "luxury", 30, []) is None


def test_get_details_returns_the_restaurant_or_none():
    client, _ = client_with(FakeResponse(200, {"id": 1, "name": "Copper Tap"}))
    assert client.get_details(1)["name"] == "Copper Tap"
    client, _ = client_with(FakeResponse(404, {"error": "not_found"}))
    assert client.get_details(999) is None


@pytest.mark.parametrize("error", [requests.Timeout("too slow"), requests.ConnectionError("refused")])
def test_network_problems_become_restaurants_unavailable(error):
    client, _ = client_with(error=error)
    with pytest.raises(RestaurantsUnavailable):
        client.list_cities()


def test_a_server_error_becomes_restaurants_unavailable():
    client, _ = client_with(FakeResponse(503, {"status": "error"}))
    with pytest.raises(RestaurantsUnavailable):
        client.get_details(1)