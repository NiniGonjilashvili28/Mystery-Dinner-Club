-- Bookings service: initial schema (moved from bookings/schema.sql, ported to SQL Server).

CREATE TABLE users (
    id            INT IDENTITY(1,1) PRIMARY KEY,
    name          NVARCHAR(100) NOT NULL,
    email         NVARCHAR(255) NOT NULL UNIQUE,
    password_hash NVARCHAR(255) NOT NULL
);

CREATE TABLE bookings (
    id              INT IDENTITY(1,1) PRIMARY KEY,
    user_id         INT NOT NULL REFERENCES users (id),
    -- Id of a restaurant in the Restaurants service, which has its own database.
    -- A foreign key is impossible across two databases; the code only saves ids
    -- that the Restaurants service returned.
    restaurant_id   INT NOT NULL,
    city            NVARCHAR(60)  NOT NULL,
    dinner_at       DATETIME2(0)  NOT NULL,
    theme_choice    NVARCHAR(20)  NOT NULL,          -- a theme, or 'random'
    budget          INT           NOT NULL CHECK (budget >= 30),
    table_number    INT           NOT NULL,
    only_new_places BIT           NOT NULL DEFAULT 0,
    rating          INT           NULL CHECK (rating BETWEEN 1 AND 5),  -- empty until rated
    comment         NVARCHAR(500) NULL,
    created_at      DATETIME2(0)  NOT NULL
);
