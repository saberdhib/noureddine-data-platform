-- Creates the airflow metadata database if it doesn't exist.
-- Runs before DDL scripts on first PostgreSQL container boot.
SELECT 'CREATE DATABASE airflow OWNER ' || current_user
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'airflow')\gexec
