"""Calls to the Restaurants service over HTTP: the seam between the two services.

These three methods replace the three functions Bookings used to import from
restaurants/service.py in Assignment 1. Every call has a timeout, and any network
problem becomes a RestaurantsUnavailable error that the caller handles.
"""
import requests


class RestaurantsUnavailable(Exception):
    """The Restaurants service did not answer in time, or answered with a server error."""


class RestaurantsClient:
    def __init__(self, base_url, timeout_s=3, session=None):
        self.base_url = base_url.rstrip("/")
        self.timeout_s = timeout_s
        self.session = session or requests.Session()

    def _call(self, method, path, json=None):
        try:
            response = self.session.request(method, self.base_url + path, json=json, timeout=self.timeout_s)
        except requests.RequestException as error:      # timeout, refused connection, DNS...
            raise RestaurantsUnavailable(str(error)) from error
        if response.status_code >= 500:
            raise RestaurantsUnavailable(f"Restaurants answered {response.status_code}")
        return response

    def list_cities(self):
        """Names of the cities that have partner restaurants."""
        response = self._call("GET", "/cities")
        return [city["city"] for city in response.json()["cities"]]

    def find_match(self, city, theme_choice, budget, exclude_ids):
        """Id of a matching restaurant, or None if nothing fits."""
        response = self._call("POST", "/matches", json={
            "city": city, "theme_choice": theme_choice, "budget": budget, "exclude_ids": list(exclude_ids),
        })
        if response.status_code == 404:
            return None
        return response.json()["restaurant_id"]

    def get_details(self, restaurant_id):
        """Name, address, offer and menu of one restaurant, or None if the id is unknown."""
        response = self._call("GET", f"/restaurants/{restaurant_id}")
        if response.status_code == 404:
            return None
        return response.json()