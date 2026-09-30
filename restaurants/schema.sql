-- Tables owned by the Restaurants domain.

CREATE TABLE IF NOT EXISTS restaurants (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    name             TEXT    NOT NULL,
    city             TEXT    NOT NULL,
    theme            TEXT    NOT NULL CHECK (theme IN ('luxury', 'cafe', 'wine_bar', 'bar', 'dessert')),
    min_budget       INTEGER NOT NULL CHECK (min_budget >= 30),
    address          TEXT    NOT NULL,
    offer_type       TEXT    NOT NULL CHECK (offer_type IN ('regular', 'special', 'discount')),
    discount_percent INTEGER NOT NULL DEFAULT 0 CHECK (discount_percent BETWEEN 0 AND 100)
);

-- Only restaurants with offer_type = 'special' have rows here.
CREATE TABLE IF NOT EXISTS menu_items (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    restaurant_id INTEGER NOT NULL REFERENCES restaurants (id),
    name          TEXT    NOT NULL,
    price         REAL    NOT NULL CHECK (price > 0)
);