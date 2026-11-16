CREATE TABLE IF NOT EXISTS users (
 id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 username varchar(64) NOT NULL UNIQUE,
 email text NOT NULL UNIQUE,
 password_hash text NOT NULL,
 bio text,
 image text,
 baseline boolean NOT NULL DEFAULT false
);
CREATE UNIQUE INDEX IF NOT EXISTS one_baseline ON users (baseline) WHERE baseline;
CREATE OR REPLACE FUNCTION protect_baseline() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF OLD.baseline THEN RAISE EXCEPTION 'immutable baseline'; END IF;
 RETURN CASE WHEN TG_OP = 'DELETE' THEN OLD ELSE NEW END;
END; $$;
DROP TRIGGER IF EXISTS immutable_baseline ON users;
CREATE TRIGGER immutable_baseline BEFORE UPDATE OR DELETE ON users FOR EACH ROW EXECUTE FUNCTION protect_baseline();
