# Mystery Dinner Club

A web app for booking surprise dinners. You choose a city, a date and time, a theme and a
budget, and the app secretly reserves a table at a partner restaurant. The restaurant is
only revealed 3 hours before the dinner.

## What it does

The app has two feature domains.

1. **Restaurants**: partner restaurants in 10 cities (Tbilisi and 9 European cities), their
   themes, minimum budgets and offers (regular menu, special menu or discount), and the
   matching logic that picks a restaurant for a booking.
2. **Bookings**: guest accounts, creating bookings (at least 3 days in advance, minimum
   budget 30€), the 3-hour reveal, visit history, ratings, and the "only new places" option.

The two domains keep their own tables. Bookings only stores a restaurant's id and asks the
Restaurants domain for everything else through `restaurants/service.py`. See `ADR.md` for
the reasons behind this and the other design decisions.

## Tech stack

- Python 3.9 or newer
- Flask (web framework, HTML templates)
- SQLite (through Python's built-in `sqlite3` module)
- pytest and pytest-cov (tests and coverage)

## Setup

```
git clone https://github.com/NiniGonjilashvili28/Mystery-Dinner-Club.git
cd Mystery-Dinner-Club
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

On Windows, activate the environment with `.venv\Scripts\activate` instead.

## Run

```
python app.py
```

Then open http://localhost:8000.

Nothing else needs to be set up. On the first start the app creates the database, the
tables and 150 sample restaurants by itself.

## Configuration

The app is configured only through environment variables. All of them are optional.

| Variable | Default | What it does |
|---|---|---|
| `PORT` | `8000` | Port the app listens on. It binds to `0.0.0.0`. |
| `DATA_DIR` | `data` | Folder for the SQLite file, which is `<DATA_DIR>/mystery_dinner.db`. |
| `SECRET_KEY` | a development value | Signs the login cookie. Set a private value when deployed. |

Example: `PORT=9000 DATA_DIR=/tmp/mystery python app.py`

## Tests

```
pytest --cov=bookings --cov=restaurants
```

Result: 75 tests pass, with 98% coverage of the two domain packages. The business logic
files (`restaurants/logic.py`, `bookings/logic.py`, both `service.py` files and
`bookings/accounts.py`) are at 100%.

## Project structure

```
app.py              starts the app and attaches both domains
db.py               opens the SQLite database and creates the tables
restaurants/        Restaurants domain
  schema.sql          its tables
  seed.py             loads the sample restaurants from seed_data.json
  logic.py            matching rules (no database, no web)
  service.py          the only functions other domains may call
  routes.py           its web pages
bookings/           Bookings domain
  schema.sql          its tables
  logic.py            booking rules (no database, no web)
  accounts.py         sign-up and login
  service.py          saves and reads bookings
  routes.py           its web pages
templates/          HTML pages
tests/              automated tests
ADR.md              architecture decisions
AI_USAGE.md         log of AI assistance
```

## Known limits

- Restaurants are sample data, not real partners.
- Payment happens at the restaurant and is not handled by the app.