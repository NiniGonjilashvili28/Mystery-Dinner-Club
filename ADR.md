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
| 2026-10-02 / faf37a6 | Claude (Opus 5.5) | Asked for sign-up and login code with hashed passwords, and tests | Accepted | | Passwords are stored as one-way hashes using generate_password_hash() instead of plain text, and check_login() uses check_password_hash() to verify them. create_user() returns None on duplicate emails because the DB UNIQUE rule blocks it. Wrong emails and wrong passwords give the exact same error message so users can't probe for valid accounts. |
| 2026-10-02 / bf5a7de | Claude (Opus 5.5) | Asked for code that saves bookings using my booking rules and the Restaurants service, and tests | Accepted | | create_booking() runs in order: parses dates, checks validate_booking(), sets exclude_ids if "only new places" is selected, calls find_restaurant_for_booking(), and executes INSERT. get_booking() keeps booking["restaurant"] as None unless is_revealed() is true so names aren't leaked. It also limits queries to the user's own ID to block unauthorized views. |
| 2026-10-02 / f9d5800 | Claude (Opus 5.5) | Asked for the Bookings pages: sign-up, login, booking form, reveal page, history and rating | Accepted | | GET fetches a page while POST submits form data. Flask's session stores user_id in a cookie signed by SECRET_KEY so it can't be tampered with. @login_required redirects unauthenticated users to login. Route functions are the only place calling datetime.now(), which gets passed directly to domain rules. |
| 2026-10-02 / dadc6e9 | Claude (Opus 5.5) | Asked for end-to-end tests of the pages using Flask's test client | Accepted | | app.test_client() simulates a web browser, and each test uses create_app() to spin up an isolated temporary DB. The status codes check basic routing: 200 (OK), 302 (redirect), and 404 (not found). These tests are brief because domain logic is already tested elsewhere. |
| 2026-10-02 / 4ca398e | Claude (Opus 5.5) | Asked for help writing ADR entry 3 about the database design | Accepted | | The DB uses 4 tables split between 2 domains. Foreign keys only exist within each domain, so bookings.restaurant_id has no formal constraint, making it easy to split into separate databases later. Ratings are stored directly as two columns on the booking table since bookings are only rated once. |
| 2026-10-02 / faf37a6 | Claude (Opus 5.5) | Asked why pytest showed 44 passed instead of 56 and accounts.py had 0% coverage, and why my AI usage table looked broken | Accepted | | The file `test_accounts.py (` wasn't recognized by pytest because of the trailing typo in its name, so the test count stayed at 44 instead of 56. My AI usage table broke because a new row was accidentally pasted onto the end of an existing line. |

## 4. Testing approach: rules first, pages last
Date: 2026-10-01
Status: Decided
Context: The assignment asks for at least 70% coverage of the core business logic, not of framework glue. My logic depends on the current time (3-day rule, 3-hour reveal) and on random choices (matching), which normally make tests unreliable.
Decision: I put the rules in `restaurants/logic.py` and `bookings/logic.py` as plain functions with no database or web code, and tested them most heavily, including edge cases like exactly 3 days, exactly 30€ and exactly the reveal time. The current time (`now`) and the random generator (`rng`) are passed in as arguments, so tests use a fixed time and a fixed seed. The service and account code is tested against a temporary SQLite database created by the `conn` fixture, and the pages only have a few end-to-end tests with Flask's test client.
Alternatives considered: Testing everything through the web pages. It would look more realistic, but each test would be slower, a failure would not show which rule broke, and time-based rules could not be tested without waiting or changing the system clock.
Consequences: There are 75 tests and 98% coverage of the two domain packages, and the logic files are at 100%. The page tests are deliberately thin, so a visual mistake in a template would not be caught. The one untested line in `restaurants/seed.py` is the "skip if restaurants already exist" path, because every test starts with an empty database.

## 5. Not built: the 3-strikes rule for no-shows
Date: 2026-09-29
Status: Decided
Context: I planned a rule where a guest who does not show up to a reserved dinner gets a strike, and three strikes ban the account, because no-shows cost partner restaurants money. To count no-shows, the app would have to know who did not come, which only the restaurant can say.
Decision: I did not build the 3-strikes rule or any attendance tracking. The app treats every past booking as a dinner the guest attended.
Alternatives considered: Building it with a staff page where restaurants mark each booking as attended or no-show. This needs staff accounts, permissions and a second kind of user, which is close to a third domain and more than the two-domain scope allows in the time I had. Letting guests confirm their own attendance, which is simpler but pointless, because a guest who skipped a dinner would just confirm it anyway.
Consequences: The app stays within two domains and I had time for tests and documentation. The cost is that nothing discourages no-shows, and a guest can rate a dinner they never went to. If it is added later, it would fit as an attendance column on `bookings` plus a strike count on `users`, both inside the Bookings domain.