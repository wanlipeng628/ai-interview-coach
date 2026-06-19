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

COMMENT ON TABLE positions IS '面试岗位表';
COMMENT ON COLUMN positions.id IS '主键ID';
COMMENT ON COLUMN positions.name IS '岗位名称';
COMMENT ON COLUMN positions.description IS '岗位描述';
COMMENT ON COLUMN positions.difficulty_level IS '岗位难度：junior/middle/senior';
COMMENT ON COLUMN positions.skill_tags IS '岗位技能标签';
COMMENT ON COLUMN positions.is_active IS '是否启用';
COMMENT ON COLUMN positions.create_time IS '创建时间';
COMMENT ON COLUMN positions.update_time IS '更新时间';

CREATE INDEX IF NOT EXISTS idx_positions_active ON positions (is_active);

CREATE TABLE IF NOT EXISTS interview_sessions (
    id BIGSERIAL PRIMARY KEY,
    session_id VARCHAR(64) NOT NULL,
    position_id BIGINT NULL,
    job_role VARCHAR(128) NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'IN_PROGRESS',
    current_round INTEGER NOT NULL DEFAULT 1,
    duration_minutes INTEGER NOT NULL DEFAULT 45,
    max_rounds INTEGER NOT NULL DEFAULT 8,
    started_at TIMESTAMP NULL,
    ended_at TIMESTAMP NULL,
    create_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    update_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uk_interview_sessions_session_id UNIQUE (session_id),
    CONSTRAINT fk_interview_sessions_position_id
        FOREIGN KEY (position_id) REFERENCES positions (id)
);

COMMENT ON TABLE interview_sessions IS '面试会话表';
COMMENT ON COLUMN interview_sessions.id IS '主键ID';
COMMENT ON COLUMN interview_sessions.session_id IS '面试会话业务ID';
COMMENT ON COLUMN interview_sessions.position_id IS '岗位ID，MVP可为空并仅使用job_role';
COMMENT ON COLUMN interview_sessions.job_role IS '面试岗位';
COMMENT ON COLUMN interview_sessions.status IS '状态：IN_PROGRESS/FINISHED/REPORTED/CANCELLED';
COMMENT ON COLUMN interview_sessions.current_round IS '当前轮次';
COMMENT ON COLUMN interview_sessions.duration_minutes IS '面试时长上限，单位分钟';
COMMENT ON COLUMN interview_sessions.max_rounds IS '最大轮次';
COMMENT ON COLUMN interview_sessions.started_at IS '开始时间';
COMMENT ON COLUMN interview_sessions.ended_at IS '结束时间';
COMMENT ON COLUMN interview_sessions.create_time IS '创建时间';
COMMENT ON COLUMN interview_sessions.update_time IS '更新时间';

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

COMMENT ON TABLE interview_messages IS '面试消息表';
COMMENT ON COLUMN interview_messages.id IS '主键ID';
COMMENT ON COLUMN interview_messages.interview_id IS '面试会话表ID';
COMMENT ON COLUMN interview_messages.role IS '消息角色：AI_INTERVIEWER/USER_CANDIDATE/SYSTEM';
COMMENT ON COLUMN interview_messages.content IS '消息内容';
COMMENT ON COLUMN interview_messages.round_no IS '面试轮次';
COMMENT ON COLUMN interview_messages.create_time IS '创建时间';
COMMENT ON COLUMN interview_messages.update_time IS '更新时间';

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

COMMENT ON TABLE interview_answer_reviews IS '面试单轮回答隐藏复盘表';
COMMENT ON COLUMN interview_answer_reviews.id IS '主键ID';
COMMENT ON COLUMN interview_answer_reviews.interview_id IS '面试会话表ID';
COMMENT ON COLUMN interview_answer_reviews.round_no IS '面试轮次';
COMMENT ON COLUMN interview_answer_reviews.evaluation IS '本轮回答评价';
COMMENT ON COLUMN interview_answer_reviews.reference_points IS '参考答题要点';
COMMENT ON COLUMN interview_answer_reviews.sample_answer IS '参考回答';
COMMENT ON COLUMN interview_answer_reviews.level IS '回答水平：good/normal/weak';
COMMENT ON COLUMN interview_answer_reviews.raw_review_json IS '模型原始复盘结构';
COMMENT ON COLUMN interview_answer_reviews.create_time IS '创建时间';
COMMENT ON COLUMN interview_answer_reviews.update_time IS '更新时间';

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

COMMENT ON TABLE interview_reports IS '面试报告表';
COMMENT ON COLUMN interview_reports.id IS '主键ID';
COMMENT ON COLUMN interview_reports.interview_id IS '面试会话表ID';
COMMENT ON COLUMN interview_reports.overall_score IS '总体评分';
COMMENT ON COLUMN interview_reports.technical_analysis IS '技术能力分析';
COMMENT ON COLUMN interview_reports.communication_analysis IS '表达能力分析';
COMMENT ON COLUMN interview_reports.weakness_points IS '薄弱知识点';
COMMENT ON COLUMN interview_reports.improvement_suggestions IS '改进建议';
COMMENT ON COLUMN interview_reports.recommended_training IS '推荐训练方向';
COMMENT ON COLUMN interview_reports.evidence_items IS '报告关键证据';
COMMENT ON COLUMN interview_reports.raw_report_json IS 'Agent原始结构化报告';
COMMENT ON COLUMN interview_reports.create_time IS '创建时间';
COMMENT ON COLUMN interview_reports.update_time IS '更新时间';

CREATE INDEX IF NOT EXISTS idx_interview_reports_interview_id
    ON interview_reports (interview_id);

CREATE OR REPLACE FUNCTION set_update_time()
RETURNS TRIGGER AS $$
BEGIN
    NEW.update_time = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_positions_update_time ON positions;
CREATE TRIGGER trg_positions_update_time
BEFORE UPDATE ON positions
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
