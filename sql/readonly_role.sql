-- run once in the Neon SQL editor as the main role
-- replace REPLACE_ME with a generated password, and never commit the real one
CREATE ROLE agent_readonly WITH LOGIN PASSWORD 'REPLACE_ME';

-- the agent can only see the analytics views, not the raw fd tables
GRANT USAGE ON SCHEMA analytics TO agent_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA analytics TO agent_readonly;

-- views are dropped and recreated on every load, so grant SELECT on future ones too
ALTER DEFAULT PRIVILEGES IN SCHEMA analytics GRANT SELECT ON TABLES TO agent_readonly;

-- safety limits
ALTER ROLE agent_readonly SET default_transaction_read_only = on;
ALTER ROLE agent_readonly SET statement_timeout = '10s';
ALTER ROLE agent_readonly SET search_path = analytics;
ALTER ROLE agent_readonly CONNECTION LIMIT 5;