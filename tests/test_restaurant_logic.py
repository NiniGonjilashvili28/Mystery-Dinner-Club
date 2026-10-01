"""Tests for the matching rules in restaurants/logic.py."""
import random

from restaurants.logic import available_themes, choose_theme, is_match, pick_restaurant

# A small, hand-made list of restaurants, so we know the right answers.
RESTAURANTS = [
    {"id": 1, "city": "Madrid", "theme": "bar", "min_budget": 30},
    {"id": 2, "city": "Madrid", "theme": "bar", "min_budget": 40},
    {"id": 3, "city": "Madrid", "theme": "luxury", "min_budget": 100},
    {"id": 4, "city": "Tbilisi", "theme": "bar", "min_budget": 30},
]


def test_is_match_true_when_everything_fits():
    assert is_match(RESTAURANTS[0], "Madrid", "bar", 50, exclude_ids=[])


def test_is_match_false_for_other_city():
    assert not is_match(RESTAURANTS[3], "Madrid", "bar", 50, exclude_ids=[])


def test_is_match_false_when_budget_too_low():
    assert not is_match(RESTAURANTS[2], "Madrid", "luxury", 99, exclude_ids=[])


def test_is_match_true_when_budget_exactly_minimum():
    assert is_match(RESTAURANTS[2], "Madrid", "luxury", 100, exclude_ids=[])


def test_is_match_false_when_already_visited():
    assert not is_match(RESTAURANTS[0], "Madrid", "bar", 50, exclude_ids=[1])


def test_available_themes_only_lists_affordable_ones():
    assert available_themes(RESTAURANTS, "Madrid", 50, exclude_ids=[]) == ["bar"]


def test_choose_theme_keeps_a_normal_choice():
    assert choose_theme("bar", RESTAURANTS, "Madrid", 50, []) == "bar"


def test_choose_theme_random_never_picks_unaffordable_theme():
    # With 50 euros, luxury (min 100) must never be chosen.
    for seed in range(20):
        assert choose_theme("random", RESTAURANTS, "Madrid", 50, [], random.Random(seed)) == "bar"


def test_choose_theme_random_returns_none_when_nothing_available():
    assert choose_theme("random", RESTAURANTS, "Paris", 50, []) is None


def test_pick_restaurant_returns_a_matching_restaurant():
    picked = pick_restaurant(RESTAURANTS, "Madrid", "bar", 50, rng=random.Random(1))
    assert picked["id"] in (1, 2)


def test_pick_restaurant_only_new_places_skips_visited():
    picked = pick_restaurant(RESTAURANTS, "Madrid", "bar", 50, exclude_ids=[1])
    assert picked["id"] == 2


def test_pick_restaurant_none_when_every_place_visited():
    assert pick_restaurant(RESTAURANTS, "Madrid", "bar", 50, exclude_ids=[1, 2]) is None


def test_pick_restaurant_none_when_budget_too_low_for_theme():
    assert pick_restaurant(RESTAURANTS, "Madrid", "luxury", 60) is None


def test_pick_restaurant_random_none_when_city_has_no_restaurants():
    assert pick_restaurant(RESTAURANTS, "Paris", "random", 50) is None