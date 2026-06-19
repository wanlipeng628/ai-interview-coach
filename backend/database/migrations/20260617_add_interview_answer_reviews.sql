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

CREATE OR REPLACE FUNCTION set_update_time()
RETURNS TRIGGER AS $$
BEGIN
    NEW.update_time = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_interview_answer_reviews_update_time ON interview_answer_reviews;
CREATE TRIGGER trg_interview_answer_reviews_update_time
BEFORE UPDATE ON interview_answer_reviews
FOR EACH ROW EXECUTE FUNCTION set_update_time();
