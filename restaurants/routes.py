"""Web pages of the Restaurants domain."""
from flask import Blueprint, render_template

from db import get_db
from restaurants.logic import THEMES
from restaurants.service import theme_counts_by_city

bp = Blueprint("restaurants", __name__)


@bp.route("/cities")
def cities():
    counts = theme_counts_by_city(get_db())
    return render_template("cities.html", counts=counts, themes=THEMES)