"""Business rules of the Restaurants domain.

These functions only work with plain Python data (lists and dictionaries).
They never touch the database or the web, so they are easy to test.
"""
import random

THEMES = ["luxury", "cafe", "wine_bar", "bar", "dessert"]


def is_match(restaurant, city, theme, budget, exclude_ids):
    """True if this restaurant fits what the guest asked for."""
    return (
        restaurant["city"] == city
        and restaurant["theme"] == theme
        and restaurant["min_budget"] <= budget
        and restaurant["id"] not in exclude_ids
    )


def available_themes(restaurants, city, budget, exclude_ids):
    """Themes that have at least one matching restaurant."""
    return [
        theme for theme in THEMES
        if any(is_match(r, city, theme, budget, exclude_ids) for r in restaurants)
    ]


def choose_theme(theme_choice, restaurants, city, budget, exclude_ids, rng=random):
    """Turn the guest's choice into a real theme.

    "random" picks one of the themes that still has a matching restaurant,
    so a random choice never fails just because of bad luck.
    Returns None if nothing is available.
    """
    if theme_choice != "random":
        return theme_choice
    options = available_themes(restaurants, city, budget, exclude_ids)
    if not options:
        return None
    return rng.choice(options)


def pick_restaurant(restaurants, city, theme_choice, budget, exclude_ids=(), rng=random):
    """Pick a secret restaurant for a booking, or None if nothing fits."""
    theme = choose_theme(theme_choice, restaurants, city, budget, exclude_ids, rng)
    if theme is None:
        return None
    candidates = [r for r in restaurants if is_match(r, city, theme, budget, exclude_ids)]
    if not candidates:
        return None
    return rng.choice(candidates)