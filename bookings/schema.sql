-- Tables owned by the Bookings domain.

CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT NOT NULL,
    email         TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS bookings (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL REFERENCES users (id),
    -- ID of a restaurant from the Restaurants domain.
    -- No FOREIGN KEY on purpose: the two domains must stay separable,
    -- so Bookings only keeps the number and asks Restaurants for details.
    restaurant_id   INTEGER NOT NULL,
    city            TEXT    NOT NULL,
    dinner_at       TEXT    NOT NULL,               -- "YYYY-MM-DD HH:MM"
    theme_choice    TEXT    NOT NULL,               -- a theme, or 'random'
    budget          INTEGER NOT NULL CHECK (budget >= 30),
    table_number    INTEGER NOT NULL,
    only_new_places INTEGER NOT NULL DEFAULT 0,     -- 0 = no, 1 = yes
    rating          INTEGER CHECK (rating BETWEEN 1 AND 5),  -- empty until rated
    comment         TEXT,
    created_at      TEXT    NOT NULL
);