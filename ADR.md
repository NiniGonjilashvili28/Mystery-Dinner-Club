# Architecture Decision Records

## 1. Backend language and framework: Python with Flask
Date: 2026-09-29
Status: Decided
Context: The app needs a small web backend that shows HTML pages and runs as a single process with SQLite. I have to be able to explain every line of it at the comprehension check, and Python is the language I am most comfortable with.
Decision: I chose Python with Flask, using Python's built-in `sqlite3` module to talk to the database.
Alternatives considered: Django, which comes with an admin panel, a user system and its own database layer, but that is much more than two small domains need and would add many files I don't need. FastAPI, which is designed for JSON APIs, but my app mainly shows web pages to people, so its extra features would not help.
Consequences: The project stays small (only 3 packages in `requirements.txt`) and easy to explain, but I have to write some things by hand that Django gives for free, such as SQL queries and a simple login. Flask Blueprints will let me keep the Restaurants and Bookings code in separate parts of the app.

## 2. Keeping the Restaurants and Bookings domains separable
Date: 2026-10-01
Status: Decided
Context: The app must be one process now, but in Assignment 2 it may be split into separate services, so the Restaurants domain (partner restaurants and matching) and the Bookings domain (guests, bookings, reveal, history and ratings) must be easy to pull apart later.
Decision: Each domain has its own folder, its own `schema.sql` with its own tables, and its own Flask Blueprint. Bookings only stores a `restaurant_id` number (no foreign key to the restaurants table) and only talks to the Restaurants domain through the functions in `restaurants/service.py`, such as `find_restaurant_for_booking()` and `get_restaurant_details()`.
Alternatives considered: Letting Bookings query the `restaurants` table directly with a SQL JOIN. It would be shorter, but it would tie the two domains to one shared database, so splitting them later would mean rewriting the Bookings code.
Consequences: `restaurants/service.py` is the seam: if Restaurants becomes its own service, those functions can be replaced by HTTP calls without changing the rest of Bookings. The cost is that the database can no longer check that a booking's `restaurant_id` is real, so the Bookings code has to check it through `get_restaurant_details()`.