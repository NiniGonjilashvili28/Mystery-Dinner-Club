"""Entry point for the Mystery Dinner Club app."""
import os

from flask import Flask

from db import close_db, get_db, init_db


def create_app(test_config=None):
    app = Flask(__name__)

    # Folder where the SQLite database file will live.
    # Can be changed with the DATA_DIR environment variable.
    data_dir = os.environ.get("DATA_DIR", "data")
    os.makedirs(data_dir, exist_ok=True)
    app.config["DATABASE"] = os.path.join(data_dir, "mystery_dinner.db")

    # Tests pass their own settings here (for example, a temporary database).
    if test_config is not None:
        app.config.update(test_config)

    # Create the tables and sample restaurants if they don't exist yet.
    init_db(app.config["DATABASE"])
    # Close the database connection at the end of every request.
    app.teardown_appcontext(close_db)

    @app.route("/")
    def home():
        db = get_db()
        restaurants = db.execute("SELECT COUNT(*) FROM restaurants").fetchone()[0]
        cities = db.execute("SELECT COUNT(DISTINCT city) FROM restaurants").fetchone()[0]
        return f"Mystery Dinner Club is running! {restaurants} partner restaurants in {cities} cities."

    return app


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    create_app().run(host="0.0.0.0", port=port)