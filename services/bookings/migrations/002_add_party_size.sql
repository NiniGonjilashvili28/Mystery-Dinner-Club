-- Data-preserving migration: every booking now records how many guests are coming.
-- Existing bookings keep all their data. They were made with a form that always
-- reserved a table for two, so SQL Server fills the new column with 2 for them.
ALTER TABLE bookings
    ADD party_size INT NOT NULL
        CONSTRAINT df_bookings_party_size DEFAULT 2
        CONSTRAINT ck_bookings_party_size CHECK (party_size BETWEEN 1 AND 8);
