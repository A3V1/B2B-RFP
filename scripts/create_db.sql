-- Create a Postgres user and database for the project
-- Run these commands (example):
-- psql -U postgres -f scripts/create_db.sql

-- Replace 'rfp_user' and 'rfp_password' with secure values, or run CREATE ROLE as needed
CREATE USER rfp_user WITH PASSWORD 'rfp_password';
CREATE DATABASE rfp_db OWNER rfp_user;
GRANT ALL PRIVILEGES ON DATABASE rfp_db TO rfp_user;
