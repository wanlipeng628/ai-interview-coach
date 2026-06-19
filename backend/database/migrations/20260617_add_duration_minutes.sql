ALTER TABLE interview_sessions
ADD COLUMN IF NOT EXISTS duration_minutes INTEGER NOT NULL DEFAULT 45;

COMMENT ON COLUMN interview_sessions.duration_minutes IS '面试时长上限，单位分钟';

UPDATE interview_sessions
SET duration_minutes = 45
WHERE duration_minutes IS NULL;
