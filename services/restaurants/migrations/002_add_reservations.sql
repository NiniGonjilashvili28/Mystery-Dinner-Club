-- Restaurants now records every table it reserves for a Mystery Dinner guest,
-- so it knows which of its tables are already taken at a given time.
CREATE TABLE reservations (
    id INT IDENTITY(1,1) PRIMARY KEY,
    restaurant_id INT NOT NULL REFERENCES restaurants(id),
    dinner_at DATETIME2(0) NOT NULL,
    table_number INT NOT NULL CHECK (table_number BETWEEN 1 AND 20),
    created_at DATETIME2(0) NOT NULL DEFAULT SYSUTCDATETIME(),
    CONSTRAINT one_guest_per_table UNIQUE (restaurant_id, dinner_at, table_number)
);
