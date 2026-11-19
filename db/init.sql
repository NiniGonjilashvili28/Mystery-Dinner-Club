-- Creates the two service databases and one login per service.
-- Idempotent: every step checks first, so running it again changes nothing.
-- The passwords are not stored here; they are passed in by docker compose (-v ...).

IF DB_ID('restaurants') IS NULL CREATE DATABASE restaurants;
GO
IF DB_ID('bookings') IS NULL CREATE DATABASE bookings;
GO

IF NOT EXISTS (SELECT 1 FROM sys.server_principals WHERE name = 'restaurants_user')
    CREATE LOGIN restaurants_user WITH PASSWORD = '$(RESTAURANTS_DB_PASSWORD)';
GO
IF NOT EXISTS (SELECT 1 FROM sys.server_principals WHERE name = 'bookings_user')
    CREATE LOGIN bookings_user WITH PASSWORD = '$(BOOKINGS_DB_PASSWORD)';
GO

-- Each login becomes a user in its own database only, so it cannot read the other one.
USE restaurants;
GO
IF NOT EXISTS (SELECT 1 FROM sys.database_principals WHERE name = 'restaurants_user')
BEGIN
    CREATE USER restaurants_user FOR LOGIN restaurants_user;
    ALTER ROLE db_owner ADD MEMBER restaurants_user;
END
GO

USE bookings;
GO
IF NOT EXISTS (SELECT 1 FROM sys.database_principals WHERE name = 'bookings_user')
BEGIN
    CREATE USER bookings_user FOR LOGIN bookings_user;
    ALTER ROLE db_owner ADD MEMBER bookings_user;
END
GO

PRINT 'Databases and logins are ready.';
GO