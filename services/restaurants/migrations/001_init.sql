-- Restaurants service: initial schema (moved from restaurants/schema.sql, ported to SQL Server).

CREATE TABLE restaurants (
    id               INT IDENTITY(1,1) PRIMARY KEY,
    name             NVARCHAR(100) NOT NULL,
    city             NVARCHAR(60)  NOT NULL,
    theme            NVARCHAR(20)  NOT NULL CHECK (theme IN ('luxury', 'cafe', 'wine_bar', 'bar', 'dessert')),
    min_budget       INT           NOT NULL CHECK (min_budget >= 30),
    address          NVARCHAR(200) NOT NULL,
    offer_type       NVARCHAR(20)  NOT NULL CHECK (offer_type IN ('regular', 'special', 'discount')),
    discount_percent INT           NOT NULL DEFAULT 0 CHECK (discount_percent BETWEEN 0 AND 100)
);

--Only restaurants with offer_type = 'special' have rows here.
CREATE TABLE menu_items (
    id            INT IDENTITY(1,1) PRIMARY KEY,
    restaurant_id INT NOT NULL REFERENCES restaurants (id),
    name          NVARCHAR(100) NOT NULL,
    price         DECIMAL(6, 2) NOT NULL CHECK (price > 0)
);