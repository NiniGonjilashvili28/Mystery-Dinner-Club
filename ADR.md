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
## 3. Database design: each domain owns its tables, linked only by an id
Date: 2026-09-30
Status: Decided
Context: Both domains must store their data in one SQLite file, but they should stay separable (ADR 2). A booking has to remember which restaurant was chosen, so the two domains' data must be connected somehow.
Decision: There are four tables. Restaurants owns `restaurants` and `menu_items`, linked by a real foreign key (`menu_items.restaurant_id` REFERENCES `restaurants`). Bookings owns `users` and `bookings`, linked by a real foreign key (`bookings.user_id` REFERENCES `users`). The only link between the two domains is `bookings.restaurant_id`, which is a plain INTEGER with no foreign key. A rating is stored as two columns on the booking (`rating`, `comment`) because each booking can be rated only once.
Alternatives considered: A foreign key from `bookings.restaurant_id` to `restaurants`, which would let the database guarantee the id is real, but it would force both domains to share one database forever. A separate `ratings` table, which would be needed if a booking could have many ratings, but with one rating per booking it would only add a table and a join.
Consequences: The two groups of tables could be moved into two separate databases without changing the schema. The cost is that the database cannot check that `restaurant_id` is real, so Bookings only saves ids it received from `find_restaurant_for_booking()`. `CHECK` rules (budget at least 30, rating 1 to 5, allowed themes) act as a second safety net behind the Python rules.