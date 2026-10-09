#!/usr/bin/env bash
# 简历助手（AIC-63）QA 复现脚本：对话式引导生成简历
#
# 用法（Git Bash / WSL / Linux）：
#   1) 启动后端：cd backend && uvicorn app.main:app --reload
#   2) 另开终端执行：bash backend/scripts/qa_resume_assistant.sh
#
# 可选环境变量：
#   BASE_URL   后端地址，默认 http://127.0.0.1:8000
#
# 依赖：curl、python（仅用于解析 JSON）
set -uo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"
API="$BASE_URL/api/resume/assistant"

# 从 JSON 字符串中按点路径取值，例如 jget "$JSON" .progress.current
jget() {
  python - "$1" "$2" <<'PY'
import json, sys

data = json.loads(sys.argv[1])
node = data
for part in sys.argv[2].strip(".").split("."):
    if not part:
        continue
    node = node[int(part)] if part.lstrip("-").isdigit() else node[part]
print(node)
PY
}

# 构造 {"key": "value"} 请求体，保证中文按 UTF-8 正确编码
body() {
  python -c 'import json,sys;print(json.dumps({sys.argv[1]: sys.argv[2]}, ensure_ascii=False))' "$1" "$2"
}

post() { curl -sS -X POST "$1" -H 'Content-Type: application/json' -d "$2"; }
get()  { curl -sS "$1"; }

echo "=================================================="
echo "场景 A：完整走通 6 个分节 -> finalize 落库"
echo "=================================================="

echo
echo "--- 1. 开始引导 ---"
START=$(post "$API/start" '{"target_role":"AI 应用开发工程师","title":"QA 测试简历"}')
echo "$START"
DRAFT_ID=$(jget "$START" .draft_id)
echo "draft_id = $DRAFT_ID"

echo
echo "--- 2. 多轮回答（覆盖 6 个分节） ---"
ask() {
  echo
  echo ">>> 用户：$1"
  RESP=$(post "$API/$DRAFT_ID/answer" "$(body answer "$1")")
  echo "$RESP"
  echo "    next_stage=$(jget "$RESP" .stage)  ready_to_finalize=$(jget "$RESP" .ready_to_finalize)"
}

ask "我叫张三，5 年工作经验，现在在北京"
ask "清华大学，计算机科学与技术，本科，2015-2019"
ask "A 公司，后端工程师，2019-2023，负责订单系统性能优化，QPS 从 500 提升到 3000"
ask "推荐系统重构，我负责召回模块，用 Python 和 Redis，难点是冷启动，上线后点击率提升 12%"
ask "Python、Go、Redis、PostgreSQL"
ask "目标岗位 AI 应用开发工程师，期望城市上海"

echo
echo "--- 3. 查询草稿状态 ---"
get "$API/$DRAFT_ID"
echo

echo
echo "--- 4. 生成并保存简历 ---"
FINALIZE=$(post "$API/$DRAFT_ID/finalize" '{}')
echo "$FINALIZE"
echo "    profile_id=$(jget "$FINALIZE" .profile_id)"

echo
echo "--- 5. 校验已落库到 resume_profiles ---"
get "$BASE_URL/api/resume/profile"
echo

echo
echo "--- 6. finalize 可迭代：重复调用应重新生成并覆盖同一份 profile_id ---"
RE_FINALIZE=$(post "$API/$DRAFT_ID/finalize" '{}')
echo "$RE_FINALIZE"
echo "    profile_id=$(jget "$RE_FINALIZE" .profile_id)（应与第 4 步一致）"

echo
echo "--- 7. 已完成草稿仍可继续补充（方案 A：不再 400） ---"
SUPPLEMENT=$(post "$API/$DRAFT_ID/answer" "$(body answer "再补充一个开源项目：我给某开源项目提过 PR，现在 star 1k")")
echo "$SUPPLEMENT"
echo "    status=$(jget "$SUPPLEMENT" .status)  stage=$(jget "$SUPPLEMENT" .stage)  ready_to_finalize=$(jget "$SUPPLEMENT" .ready_to_finalize)"

echo
echo "--- 8. 补充后重新生成：profile_id 不变、内容应反映新增信息 ---"
REGEN=$(post "$API/$DRAFT_ID/finalize" '{}')
echo "$REGEN"
echo "    profile_id=$(jget "$REGEN" .profile_id)"

echo
echo "--- 9. 错误提示应为中文（404 不应透出英文 detail） ---"
curl -sS "$API/not-a-real-draft"
echo

echo
echo "=================================================="
echo "场景 B：引导行为（追问 / 跳节 / 主动结束）"
echo "=================================================="

DRAFT_B=$(jget "$(post "$API/start" '{}')" .draft_id)

echo
echo "--- B1. 简略回答应触发追问（stage 不变） ---"
post "$API/$DRAFT_B/answer" "$(body answer "做了些优化")"
echo

echo
echo "--- B2. 明确说「没有」应跳过该节（stage 推进，无需 LLM） ---"
SKIP=$(post "$API/$DRAFT_B/answer" "$(body answer "没有")")
echo "$SKIP"
echo "    新 stage = $(jget "$SKIP" .stage)"

echo
echo "--- B3. 分节未齐时说「够了，帮我生成吧」→ 只提示未完成分节，不置 COMPLETED ---"
PENDING=$(post "$API/$DRAFT_B/answer" "$(body answer "够了，帮我生成吧")")
echo "$PENDING"
echo "    status=$(jget "$PENDING" .status)（应为 IN_PROGRESS）  ready_to_finalize=$(jget "$PENDING" .ready_to_finalize)（应为 False）"
echo "    progress.completed=$(jget "$PENDING" .progress.completed)（不得 6 节全绿）"

echo
echo "--- B4. 对剩余分节逐一「没有」跳过后，草稿才置 COMPLETED ---"
for _ in 1 2 3 4 5 6; do
  RESP=$(post "$API/$DRAFT_B/answer" "$(body answer "没有")")
  STAGE=$(jget "$RESP" .stage)
  echo "    -> stage=$STAGE  status=$(jget "$RESP" .status)"
  if [ "$STAGE" = "DONE" ]; then break; fi
done

echo
echo "--- B5. 完成收集后生成并保存简历 ---"
post "$API/$DRAFT_B/finalize" '{}'
echo

echo
echo "--- B6. 不存在的 draft 应返回 404 + 中文 detail ---"
curl -sS -o /dev/null -w "HTTP %{http_code}\n" "$API/not-a-real-draft"

echo
echo "--- B7. 空白回答应返回 400 + 中文 detail ---"
curl -sS -X POST "$API/$DRAFT_B/answer" -H 'Content-Type: application/json' -d "$(body answer '   ')"

echo
echo "--- B8. 空回答（空字符串）应返回 400 + 中文 detail ---"
curl -sS -X POST "$API/$DRAFT_B/answer" -H 'Content-Type: application/json' -d '{"answer": ""}'

echo
echo "全部场景执行完毕。"
