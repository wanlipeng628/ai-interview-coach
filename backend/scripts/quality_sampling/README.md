# AIC-80 关思考/开思考对比样本采集脚本

一次性取数工具，不属于业务代码，不被 `app/` 任何模块引用。用途：按 AIC-80《固定输入包 v1》第 6 节，对同样 12 个场景先跑 `LLM_QUESTION_THINKING=disabled`（Batch A）、再跑 `enabled`（Batch B），导出第 7 节规定的 JSONL。

## 依赖

- Python 3.11，仓库 `backend/` 下已有的依赖（`pip install -e .` 或容器内环境均可）
- 一个能访问**生产同源网关**的凭据：`LLM_API_KEY` + `LLM_BASE_URL` + `LLM_MODEL=deepseek-v4-flash`

脚本在进程内直接实例化 `InterviewerAgent` / `InterviewService`，不走 HTTP、不连数据库、不读写任何线上容器，因此不需要起服务，也不需要动 `/opt/ai-coach/.env`。`LLM_QUESTION_THINKING` 是通过改进程内 `settings.llm_question_thinking` 切换的——`InterviewerAgent` 每次调用都读这个值，效果与线上改环境变量等价。

## 文件

| 路径 | 说明 |
|------|------|
| `run_sampling.py` | 主脚本 |
| `scenes.json` | 12 个场景（场景 / 简历 / 岗位 / direction / mode） |
| `resumes/R1..R6.txt` | 输入包第 3 节的 6 份简历原文 |
| `simulator_prompt.txt` | 输入包 5.2 的候选人模拟器 prompt 原文 |
| `out/` | 运行产物，已 gitignore |

## 自检（不需要任何凭据）

```bash
cd backend
python scripts/quality_sampling/run_sampling.py --mock --out-dir scripts/quality_sampling/out/_mock
```

`--mock` 用确定性假客户端跑完整流程，会人为制造重试、JSON 解析失败、重复题触发重生成等分支，用来校验脚本本身。**mock 产物是假数据，只能用来验脚本，不能用于任何质量结论。**

## 正式跑批

```bash
cd backend
LLM_API_KEY=<生产同源网关的 key> \
LLM_BASE_URL=https://token.sensenova.cn/v1 \
LLM_MODEL=deepseek-v4-flash \
python scripts/quality_sampling/run_sampling.py --group all
```

- `--group all` 先跑 Batch A（disabled）再跑 Batch B（enabled），两组之间默认停 30 秒；只跑其中一组用 `--group disabled` / `--group enabled`。
- 规模约 192 次出题 + 96 次模拟器调用，串行 1~1.5 小时，务必在一个 30 分钟窗口内不间断跑完两组。
- `temperature` 固定 0.7，脚本会拒绝其他取值。
- 模型不是 `deepseek-v4-flash` 时脚本默认拒绝启动；确实要用代理模型，得显式加 `--allow-model-mismatch`，并接受结论失去对线上的外推能力。
- 中途断掉直接重跑同一条命令即可：脚本按 `sample_id` / `session_id` 续跑，不会重复写入已有记录。

## 产物

`out/aic80-<UTC时间>/` 下：

- `samples.jsonl` — 每条样本一行，字段见输入包 7.1
- `session_meta.jsonl` — 每个完整面试场的元信息
- `errors.jsonl` — 生成失败的记录
- `run_meta.json` — 两组的起止时间、模型、prompt 版本等
- `README.md` — 输入包 7.3 要求的跑批说明（时间窗、模型实际值、prompt 版本、枚举映射、模拟器参数、重试记录、每场模拟器平均回答长度）

## 已知口径偏差

完整清单写在每次运行的 `out/aic80-<UTC>/README.md` 第 11 节。最重要的一条：产品 `start_interview()` 的第 1 题是静态模板（自我介绍），LLM 第一次真正出题是线上的第 2 轮；本脚本按抽检标准 §2.1 的口径，把「无历史上下文时 LLM 生成的第一题」记为第 1 轮，因此这批样本的第 1 轮不等同于线上用户看到的第一句话。
