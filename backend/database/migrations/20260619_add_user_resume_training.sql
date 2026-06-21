CREATE TABLE IF NOT EXISTS users (
    id BIGSERIAL PRIMARY KEY,
    username VARCHAR(64) NOT NULL UNIQUE,
    display_name VARCHAR(128) NULL,
    email VARCHAR(128) NULL,
    password_hash VARCHAR(255) NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'ACTIVE',
    create_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    update_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO users (id, username, display_name)
VALUES (1, 'default_user', '默认用户')
ON CONFLICT (id) DO NOTHING;

CREATE TABLE IF NOT EXISTS resume_profiles (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    title VARCHAR(128) NOT NULL,
    content TEXT NOT NULL,
    summary TEXT NULL,
    is_default BOOLEAN NOT NULL DEFAULT TRUE,
    create_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    update_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_resume_profiles_user_id
        FOREIGN KEY (user_id) REFERENCES users (id)
);

CREATE INDEX IF NOT EXISTS idx_resume_profiles_user_id ON resume_profiles (user_id);
CREATE INDEX IF NOT EXISTS idx_resume_profiles_default ON resume_profiles (user_id, is_default);

ALTER TABLE interview_sessions
ADD COLUMN IF NOT EXISTS user_id BIGINT NOT NULL DEFAULT 1,
ADD COLUMN IF NOT EXISTS direction VARCHAR(64) NULL,
ADD COLUMN IF NOT EXISTS interviewer_mode VARCHAR(64) NULL,
ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS is_valid BOOLEAN NOT NULL DEFAULT TRUE;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'fk_interview_sessions_user_id'
    ) THEN
        ALTER TABLE interview_sessions
        ADD CONSTRAINT fk_interview_sessions_user_id
        FOREIGN KEY (user_id) REFERENCES users (id);
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_interview_sessions_user_id ON interview_sessions (user_id);

CREATE TABLE IF NOT EXISTS training_tasks (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    source_session_id VARCHAR(64) NULL,
    title VARCHAR(128) NOT NULL,
    reason TEXT NULL,
    severity VARCHAR(32) NOT NULL DEFAULT 'Medium',
    status VARCHAR(32) NOT NULL DEFAULT 'TODO',
    create_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    update_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_training_tasks_user_id
        FOREIGN KEY (user_id) REFERENCES users (id)
);

CREATE INDEX IF NOT EXISTS idx_training_tasks_user_id ON training_tasks (user_id);
CREATE INDEX IF NOT EXISTS idx_training_tasks_status ON training_tasks (user_id, status);

CREATE OR REPLACE FUNCTION set_update_time()
RETURNS TRIGGER AS $$
BEGIN
    NEW.update_time = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_users_update_time ON users;
CREATE TRIGGER trg_users_update_time
BEFORE UPDATE ON users
FOR EACH ROW EXECUTE FUNCTION set_update_time();

DROP TRIGGER IF EXISTS trg_resume_profiles_update_time ON resume_profiles;
CREATE TRIGGER trg_resume_profiles_update_time
BEFORE UPDATE ON resume_profiles
FOR EACH ROW EXECUTE FUNCTION set_update_time();

DROP TRIGGER IF EXISTS trg_training_tasks_update_time ON training_tasks;
CREATE TRIGGER trg_training_tasks_update_time
BEFORE UPDATE ON training_tasks
FOR EACH ROW EXECUTE FUNCTION set_update_time();
