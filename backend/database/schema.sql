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

CREATE TABLE IF NOT EXISTS positions (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(128) NOT NULL,
    description TEXT NULL,
    difficulty_level VARCHAR(32) NOT NULL DEFAULT 'middle',
    skill_tags JSONB NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    create_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    update_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_positions_active ON positions (is_active);

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

CREATE TABLE IF NOT EXISTS interview_sessions (
    id BIGSERIAL PRIMARY KEY,
    session_id VARCHAR(64) NOT NULL,
    user_id BIGINT NOT NULL DEFAULT 1,
    position_id BIGINT NULL,
    job_role VARCHAR(128) NOT NULL,
    direction VARCHAR(64) NULL,
    interviewer_mode VARCHAR(64) NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'IN_PROGRESS',
    current_round INTEGER NOT NULL DEFAULT 1,
    duration_minutes INTEGER NOT NULL DEFAULT 45,
    max_rounds INTEGER NOT NULL DEFAULT 999,
    started_at TIMESTAMP NULL,
    ended_at TIMESTAMP NULL,
    is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
    is_valid BOOLEAN NOT NULL DEFAULT TRUE,
    create_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    update_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uk_interview_sessions_session_id UNIQUE (session_id),
    CONSTRAINT fk_interview_sessions_user_id
        FOREIGN KEY (user_id) REFERENCES users (id),
    CONSTRAINT fk_interview_sessions_position_id
        FOREIGN KEY (position_id) REFERENCES positions (id)
);

CREATE INDEX IF NOT EXISTS idx_interview_sessions_user_id ON interview_sessions (user_id);
CREATE INDEX IF NOT EXISTS idx_interview_sessions_status ON interview_sessions (status);
CREATE INDEX IF NOT EXISTS idx_interview_sessions_position_id ON interview_sessions (position_id);

CREATE TABLE IF NOT EXISTS interview_messages (
    id BIGSERIAL PRIMARY KEY,
    interview_id BIGINT NOT NULL,
    role VARCHAR(32) NOT NULL,
    content TEXT NOT NULL,
    round_no INTEGER NOT NULL,
    create_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    update_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_interview_messages_interview_id
        FOREIGN KEY (interview_id) REFERENCES interview_sessions (id)
        ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_interview_messages_interview_id
    ON interview_messages (interview_id);
CREATE INDEX IF NOT EXISTS idx_interview_messages_round
    ON interview_messages (interview_id, round_no);

CREATE TABLE IF NOT EXISTS interview_answer_reviews (
    id BIGSERIAL PRIMARY KEY,
    interview_id BIGINT NOT NULL,
    round_no INTEGER NOT NULL,
    evaluation TEXT NOT NULL,
    reference_points JSONB NOT NULL,
    sample_answer TEXT NOT NULL,
    level VARCHAR(32) NOT NULL,
    raw_review_json JSONB NULL,
    create_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    update_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uk_interview_answer_reviews_round UNIQUE (interview_id, round_no),
    CONSTRAINT fk_interview_answer_reviews_interview_id
        FOREIGN KEY (interview_id) REFERENCES interview_sessions (id)
        ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_interview_answer_reviews_interview_id
    ON interview_answer_reviews (interview_id);

CREATE TABLE IF NOT EXISTS interview_reports (
    id BIGSERIAL PRIMARY KEY,
    interview_id BIGINT NOT NULL,
    overall_score NUMERIC(5, 2) NULL,
    technical_analysis TEXT NULL,
    communication_analysis TEXT NULL,
    weakness_points JSONB NULL,
    improvement_suggestions JSONB NULL,
    recommended_training JSONB NULL,
    evidence_items JSONB NULL,
    raw_report_json JSONB NULL,
    create_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    update_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uk_interview_reports_interview_id UNIQUE (interview_id),
    CONSTRAINT fk_interview_reports_interview_id
        FOREIGN KEY (interview_id) REFERENCES interview_sessions (id)
        ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_interview_reports_interview_id
    ON interview_reports (interview_id);

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

CREATE TABLE IF NOT EXISTS training_sessions (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    task_id BIGINT NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'IN_PROGRESS',
    current_round INTEGER NOT NULL DEFAULT 1,
    ended_at TIMESTAMP NULL,
    create_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    update_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_training_sessions_user_id
        FOREIGN KEY (user_id) REFERENCES users (id),
    CONSTRAINT fk_training_sessions_task_id
        FOREIGN KEY (task_id) REFERENCES training_tasks (id)
        ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_training_sessions_user_id ON training_sessions (user_id);
CREATE INDEX IF NOT EXISTS idx_training_sessions_task_id ON training_sessions (task_id);
CREATE INDEX IF NOT EXISTS idx_training_sessions_status ON training_sessions (user_id, status);

CREATE TABLE IF NOT EXISTS training_messages (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    training_session_id BIGINT NOT NULL,
    role VARCHAR(32) NOT NULL,
    content TEXT NOT NULL,
    round_no INTEGER NOT NULL,
    feedback TEXT NULL,
    reference_points JSONB NULL,
    sample_answer TEXT NULL,
    create_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    update_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_training_messages_user_id
        FOREIGN KEY (user_id) REFERENCES users (id),
    CONSTRAINT fk_training_messages_session_id
        FOREIGN KEY (training_session_id) REFERENCES training_sessions (id)
        ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_training_messages_session_id
    ON training_messages (training_session_id);
CREATE INDEX IF NOT EXISTS idx_training_messages_round
    ON training_messages (training_session_id, round_no);

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

DROP TRIGGER IF EXISTS trg_positions_update_time ON positions;
CREATE TRIGGER trg_positions_update_time
BEFORE UPDATE ON positions
FOR EACH ROW EXECUTE FUNCTION set_update_time();

DROP TRIGGER IF EXISTS trg_resume_profiles_update_time ON resume_profiles;
CREATE TRIGGER trg_resume_profiles_update_time
BEFORE UPDATE ON resume_profiles
FOR EACH ROW EXECUTE FUNCTION set_update_time();

DROP TRIGGER IF EXISTS trg_interview_sessions_update_time ON interview_sessions;
CREATE TRIGGER trg_interview_sessions_update_time
BEFORE UPDATE ON interview_sessions
FOR EACH ROW EXECUTE FUNCTION set_update_time();

DROP TRIGGER IF EXISTS trg_interview_messages_update_time ON interview_messages;
CREATE TRIGGER trg_interview_messages_update_time
BEFORE UPDATE ON interview_messages
FOR EACH ROW EXECUTE FUNCTION set_update_time();

DROP TRIGGER IF EXISTS trg_interview_answer_reviews_update_time ON interview_answer_reviews;
CREATE TRIGGER trg_interview_answer_reviews_update_time
BEFORE UPDATE ON interview_answer_reviews
FOR EACH ROW EXECUTE FUNCTION set_update_time();

DROP TRIGGER IF EXISTS trg_interview_reports_update_time ON interview_reports;
CREATE TRIGGER trg_interview_reports_update_time
BEFORE UPDATE ON interview_reports
FOR EACH ROW EXECUTE FUNCTION set_update_time();

DROP TRIGGER IF EXISTS trg_training_tasks_update_time ON training_tasks;
CREATE TRIGGER trg_training_tasks_update_time
BEFORE UPDATE ON training_tasks
FOR EACH ROW EXECUTE FUNCTION set_update_time();

DROP TRIGGER IF EXISTS trg_training_sessions_update_time ON training_sessions;
CREATE TRIGGER trg_training_sessions_update_time
BEFORE UPDATE ON training_sessions
FOR EACH ROW EXECUTE FUNCTION set_update_time();

DROP TRIGGER IF EXISTS trg_training_messages_update_time ON training_messages;
CREATE TRIGGER trg_training_messages_update_time
BEFORE UPDATE ON training_messages
FOR EACH ROW EXECUTE FUNCTION set_update_time();
