"""Entry point for the Mystery Dinner Club app."""
import os

from flask import Flask, render_template

from bookings.routes import bp as bookings_bp
from db import close_db, init_db
from restaurants.routes import bp as restaurants_bp


def create_app(test_config=None):
    app = Flask(__name__)

    # Folder where the SQLite database file will live.
    # Can be changed with the DATA_DIR environment variable.
    data_dir = os.environ.get("DATA_DIR", "data")
    os.makedirs(data_dir, exist_ok=True)
    app.config["DATABASE"] = os.path.join(data_dir, "mystery_dinner.db")

    # Secret used to sign the login cookie. Set SECRET_KEY to a private value when deployed.
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-only-change-me")

    # Tests pass their own settings here (for example, a temporary database).
    if test_config is not None:
        app.config.update(test_config)

    # Create the tables and sample restaurants if they don't exist yet.
    init_db(app.config["DATABASE"])
    # Close the database connection at the end of every request.
    app.teardown_appcontext(close_db)

    # Attach the pages of each domain.
    app.register_blueprint(restaurants_bp)
    app.register_blueprint(bookings_bp)

    @app.route("/")
    def home():
        return render_template("home.html")

    return app


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    create_app().run(host="0.0.0.0", port=port)