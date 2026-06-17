-- Create rag_readonly role. Grants are applied after migrations by entrypoint.sh.
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'rag_readonly') THEN
        CREATE ROLE rag_readonly;
    END IF;
END $$;
