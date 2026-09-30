# Architecture Decision Records

## 1. Backend language and framework: Python with Flask
Date: 2026-09-29
Status: Decided
Context: The app needs a small web backend that shows HTML pages and runs as a single process with SQLite. I have to be able to explain every line of it at the comprehension check, and Python is the language I am most comfortable with.
Decision: I chose Python with Flask, using Python's built-in `sqlite3` module to talk to the database.
Alternatives considered: Django, which comes with an admin panel, a user system and its own database layer, but that is much more than two small domains need and would add many files I don't need. FastAPI, which is designed for JSON APIs, but my app mainly shows web pages to people, so its extra features would not help.
Consequences: The project stays small (only 3 packages in `requirements.txt`) and easy to explain, but I have to write some things by hand that Django gives for free, such as SQL queries and a simple login. Flask Blueprints will let me keep the Restaurants and Bookings code in separate parts of the app.