-- PostgreSQL initialization script for K6 testing
-- This script is executed when the PostgreSQL container starts

-- Create additional database for testing isolation
CREATE DATABASE test_k6_db_backup;

-- Grant all privileges to the postgres user for both databases
GRANT ALL PRIVILEGES ON DATABASE test_k6_db TO postgres;
GRANT ALL PRIVILEGES ON DATABASE test_k6_db_backup TO postgres;

-- Set some optimized settings for testing
ALTER SYSTEM SET max_connections = 200;
ALTER SYSTEM SET shared_buffers = '256MB';
ALTER SYSTEM SET effective_cache_size = '1GB';
ALTER SYSTEM SET maintenance_work_mem = '64MB';
ALTER SYSTEM SET random_page_cost = 1.1;
ALTER SYSTEM SET effective_io_concurrency = 200;

-- Reload configuration
SELECT pg_reload_conf();