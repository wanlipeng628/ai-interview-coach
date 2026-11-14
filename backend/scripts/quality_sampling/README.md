# 出题质量抽样脚本

一次性取数工具，不属于业务代码，不被 `app/` 任何模块引用。用途：按固定输入包对同样 12 个场景
分别跑 `LLM_QUESTION_THINKING=disabled`（Batch A）和 `enabled`（Batch B），导出 JSONL 供人工盲评。

> **脆弱点**：这是外挂脚本，不在 `app/` 依赖里。出题链路接口一改它就会跑不起来
> （AIC-82 把同步生成器换成 async 版本时打断过一次）。改完出题链路记得回归它。

## 依赖

- Python 3.11，仓库 `backend/` 下已有的依赖（`pip install -e .` 或容器内环境均可）
- 一个能访问**生产同源网关**的凭据：`LLM_API_KEY` + `LLM_BASE_URL` + `LLM_MODEL=deepseek-flash`

脚本在进程内直接实例化 `InterviewerAgent` / `InterviewService`，不走 HTTP、不连数据库、
不读写任何线上容器，因此不需要起服务，也不需要动 `/opt/ai-coach/.env`。
`LLM_QUESTION_THINKING` 是通过改进程内 `settings.llm_question_thinking` 切换的——
`InterviewerAgent` 每次调用都读这个值，效果与线上改环境变量等价。

模型别名必须与生产一致，否则脚本拒绝启动（确实要用别的模型得显式加
`--allow-model-mismatch`，但结论就失去对线上的外推能力，引用数据时必须注明）。

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

`--mock` 用确定性假客户端跑完整流程，会人为制造重试、JSON 解析失败、重复题触发重生成等分支，
用来校验脚本本身。**mock 产物是假数据，只能验脚本，不能用于任何质量结论。**

## 常用跑法

```bash
cd backend
LLM_API_KEY=<生产同源网关的 key> \
LLM_BASE_URL=https://api.deepseek.com/v1 \
LLM_MODEL=deepseek-flash \
python scripts/quality_sampling/run_sampling.py --group all
```

### 参数怎么选

| 目标 | 参数 |
|---|---|
| 两组全量对比（单题 + 完整面试） | `--group all`（默认 3 单题 × 12 场景 + 12 场 × 5 轮） |
| **只测追问质量**（推荐） | `--single-samples 0 --rounds 5`：12 场 × 5 轮，每组 48 道追问 |
| 只测开场题 | `--only-single --single-samples 3` |
| 少量验证（改完规则先跑这个） | `--scenes S04,S07,S11 --single-samples 0 --rounds 5` |

**比较延迟时不要用开场题**：自我介绍没有思考成本，开/关思考的首 token 都会落在 1.3 秒左右，
会得出「两组一样快」的错误结论。追问题才有区分度（实测 627ms vs 2792ms）。

其它行为：

- `--group all` 先跑 A（disabled）再跑 B（enabled），两组之间默认停 30 秒，`--gap-seconds` 可调
- `temperature` 固定 0.7，脚本拒绝其他取值
- 中途断掉直接重跑同一条命令即可：脚本按 `sample_id` / `session_id` 续跑，不会重复写入

## 产物

`out/aic80-<UTC时间>/` 下：

- `samples.jsonl` — 每条样本一行（字段见输入包 7.1），含 `multi_question_detected` /
  `multi_question_final` / `regen_triggered` / `regen_reason` 等质量标记
- `session_meta.jsonl` — 每个完整面试场的元信息
- `errors.jsonl` — 生成失败的记录
- `run_meta.json` — 两组的起止时间、模型、prompt 版本等
- `README.md` — 跑批说明（时间窗、模型实际值、prompt 版本、枚举映射、模拟器参数、重试记录、平均回答长度）

`prompt_version` 形如 `git:b793fbf;interviewer_prompt:sha256-996e94d55bc2`。工作区有未提交改动时
会记成 `git:b793fbf+dirty:1a2b3c4d;…`——这种样本不能用 HEAD 复现，引用数据时要连 `+dirty` 一起标注。

## 怎么用这批数据

**不要只看计数器。** `multi_question_final = 0` 是「计数器口径下为 0」，不是「人工口径下为 0」。
AIC-85 那次 96 道追问里有 13 道实际是两问，而所有计数位都是 false。

正确做法：把题面导出来人工盲评（先评分后解盲），或者拿历史标注集做回归。
详见 `docs/question-quality.md`。

## 已知口径偏差

完整清单写在每次运行的 `out/aic80-<UTC>/README.md` 第 11 节。最重要的一条：
产品 `start_interview()` 的第 1 题是静态模板（自我介绍），LLM 第一次真正出题是线上的第 2 轮；
本脚本把「无历史上下文时 LLM 生成的第一题」记为第 1 轮，因此这批样本的第 1 轮不等同于
线上用户看到的第一句话。
