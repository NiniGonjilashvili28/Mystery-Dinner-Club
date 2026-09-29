"""Entry point for the Mystery Dinner Club app."""
import os

from flask import Flask

#This is a common pattern called an app factory.(simple factory)
def create_app():
    app = Flask(__name__)

    # Folder where the SQLite database file will live.
    # Can be changed with the DATA_DIR environment variable.
    data_dir = os.environ.get("DATA_DIR", "data")
    os.makedirs(data_dir, exist_ok=True)
    app.config["DATABASE"] = os.path.join(data_dir, "mystery_dinner.db")

    @app.route("/")
    def home():
        return "Mystery Dinner Club is running!"

    return app


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    create_app().run(host="0.0.0.0", port=port)