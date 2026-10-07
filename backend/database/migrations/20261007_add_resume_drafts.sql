-- 简历助手：对话式草稿表（AIC-63）
CREATE TABLE IF NOT EXISTS resume_drafts (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    session_id VARCHAR(64) NOT NULL UNIQUE,
    status VARCHAR(16) NOT NULL DEFAULT 'IN_PROGRESS',
    stage VARCHAR(16) NOT NULL DEFAULT 'BASIC',
    messages JSONB NOT NULL DEFAULT '[]',
    sections JSONB NOT NULL DEFAULT '{}',
    follow_up_count INT NOT NULL DEFAULT 0,
    target_role VARCHAR(128) NULL,
    title VARCHAR(128) NOT NULL DEFAULT '默认简历',
    profile_id BIGINT NULL,
    create_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    update_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_resume_drafts_user_id
        FOREIGN KEY (user_id) REFERENCES users (id)
);

CREATE INDEX IF NOT EXISTS idx_resume_drafts_user_id ON resume_drafts (user_id);
CREATE INDEX IF NOT EXISTS idx_resume_drafts_session_id ON resume_drafts (session_id);

CREATE OR REPLACE FUNCTION set_update_time()
RETURNS TRIGGER AS $$
BEGIN
    NEW.update_time = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_resume_drafts_update_time ON resume_drafts;
CREATE TRIGGER trg_resume_drafts_update_time
BEFORE UPDATE ON resume_drafts
FOR EACH ROW EXECUTE FUNCTION set_update_time();
