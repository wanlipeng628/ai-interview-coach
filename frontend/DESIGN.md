# AI 面试教练 · 前端设计系统

设计路线：克制统一。**不改视觉风格，只消除不一致**。全站共用一套 token、卡片变体和页头模式。

---

## 设计 Token

唯一真值源：`src/assets/styles/_tokens.scss`。同时导出为 CSS 变量（运行时可用）和 JS 镜像（`src/assets/styles/tokens.ts`，供 ECharts 等使用）。

组件样式禁止硬编码裸 hex / rgb，一律通过 token 引用。

### 色板

| 分类 | Token | 值 | 用途 |
|---|---|---|---|
| 品牌色 | `--c-primary-500` | `#2f6bff` | 主按钮、链接、激活态 |
| 文本 | `--c-text-primary` | `#101828` | 标题、正文主色 |
| 文本 | `--c-text-secondary` | `#475467` | 次级说明、元信息 |
| 文本 | `--c-text-tertiary` | `#667085` | 占位、辅助文案 |
| 文本 | `--c-text-quaternary` | `#98a2b3` | 禁用、纯装饰 |
| 成功 | `--c-success-text` | `#067647` | 白底 AA+ 文本档 |
| 成功 | `--c-success` | `#17a568` | 图形档（按钮/图标） |
| 警示 | `--c-warning-text` | `#b54708` | 白底 AA 文本档 |
| 危险 | `--c-danger-text` | `#b42318` | 白底 AA+ 文本档 |
| 页面底 | `--c-bg-page` | `#f5f7fb` | 最外层页面背景 |
| 卡片底 | `--c-bg-card` | `#ffffff` | 浮卡底色 |
| 衬底 | `--c-bg-tint` | `#f7f9fc` | 次级内容区、消息列表底 |
| 描边 | `--c-border` | `#e4e7ec` | 卡片、输入框描边 |
| 分隔 | `--c-border-light` | `#f2f4f7` | 列表细分隔 |
| 深色底 | `--c-dark-bg` | `#0e1629` | 侧栏 / 移动端顶栏 |
| 深色文本 | `--c-dark-text` | `#e9eefc` | 深色底主文本 |
| 反色文本 | `--c-text-inverse` | `#ffffff` | 彩色底上的白字 |
| 图表紫 | `--c-chart-purple` | `#7a5af8` | 图表扩展色 / 学习时长强调 |

语义色每色 3 档：`-text`（白底 AA 文本档）、基础色（图形档）、`-light`（浅底填充）。

### 圆角

| Token | 值 | 用途 |
|---|---|---|
| `--r-sm` | 6px | 标签、小按钮 |
| `--r-md` | 8px | 默认：卡片、按钮、输入框 |
| `--r-lg` | 12px | 强调卡（`is-emphasis` 修饰符） |

默认 8px，强调卡 12px。全站不超过两档视觉权重。

### 阴影

| Token | 值 | 用途 |
|---|---|---|
| `--sh-sm` | 0 1px 2px rgba(16,24,40,.04) | 细微抬升 / hover |
| `--sh-md` | 0 4px 12px rgba(16,24,40,.06) | 标准浮卡（float 变体） |
| `--sh-lg` | 0 12px 30px rgba(19,34,66,.08) | 强调卡（is-emphasis）、抽屉 |
| `--sh-xl` | 0 20px 48px rgba(19,34,66,.12) | 模态框 |

### 字阶

共 9 档，16px = 1rem 基准：

| Token | 大小 | 用途 |
|---|---|---|
| `--fs-xs` | 12px | 辅助标注、标签 |
| `--fs-sm` | 13px | 元信息、说明行、eyebrow |
| `--fs-base` | 14px | 正文默认 |
| `--fs-md` | 15px | 次级标题、列表项 |
| `--fs-lg` | 17px | 卡片标题 h2 |
| `--fs-xl` | 20px | 页头 h1（移动端） |
| `--fs-2xl` | 24px | 页头 h1（桌面端） |
| `--fs-3xl` | 28px | 首页欢迎区标题 |
| `--fs-4xl` / `--fs-5xl` | 48 / 64px | 报告总分（移动/桌面） |

字重 3 档：`--fw-regular` 400、`--fw-semibold` 600、`--fw-bold` 700。中文不用 800（与 700 视觉差异可忽略）。

---

## 卡片变体系统

基于 `el-card`，通过双 class 选择器（`.card.card--xxx`）覆盖样式，不依赖 import 顺序。

在 `<el-card>` 上加 `class="card card--{variant}"` 使用。

### 变体

| 变体 | 类名 | 视觉特征 | 适用场景 |
|---|---|---|---|
| float | `.card.card--float` | 白卡 + `--sh-md` 阴影 + 无边框 | 主内容卡、大多数场景 |
| flat | `.card.card--flat` | 白卡 + 1px 描边 + 无阴影 | 列表区、次级内容 |
| tint | `.card.card--tint` | 浅衬底 + 无边框 + 无阴影 | 嵌入式内容背景、提示区 |

### 强调修饰符

`.card.is-emphasis`：`--r-lg` 大圆角 + `--sh-lg` 大阴影 + 加厚内边距。一页最多一张，用来突出核心指标（首页欢迎卡、报告总分卡）。

### 卡片标题

统一用 `<template #header><h2>标题</h2></template>` 模式。`_cards.scss` 已定义 `.card__header` 统一排版（h2 17px semibold + p 13px tertiary）。

---

## 页头模式

统一组件：`<PageHeader>`（`src/components/common/PageHeader.vue`）。

### 三变体

| 变体 | variant | 视觉 | 适用页面 |
|---|---|---|---|
| card（默认） | `card` | 白色浮卡，24px 内边距 | 历史页、报告页、能力画像、训练列表、简历档案 |
| toolbar | `toolbar` | 更小字号，工具栏样式 | 面试间顶部 |
| plain | `plain` | 无卡包装，嵌入内容中，标题最大 28px | 训练详情、面试准备页 |

### Props

```ts
defineProps<{
  title?: string
  eyebrow?: string       // 小标题，灰色 + 字间距，仅首页/历史/报告三页使用
  description?: string   // 描述行，仅首页/历史/报告三页使用
  variant?: 'card' | 'toolbar' | 'plain'
  emphasis?: boolean     // 是否为强调卡（仅 card 变体）
}>()
```

### Slots

- 默认 slot：标题内容（不传 `title` prop 时用）
- `#leading`：标题左侧（如返回按钮）
- `#actions`：右侧操作区

### 移动端规则

- card 变体：内容区换列，actions 全宽铺开
- toolbar 变体：保持横向不换行（面试间特有）
- plain 变体：标题降档到 22px

---

## 响应式

断点定义：`src/assets/styles/_responsive.scss`

| 断点 | 混入 | 宽度 | 说明 |
|---|---|---|---|
| 移动端 | `@include mobile` | ≤768px | Tabbar、单栏布局 |
| 图标栏 | `@include icon-rail` | 769–1023px | 侧栏收为图标列 |
| 桌面 | 默认 | ≥1024px | 完整侧栏 + 双/三栏布局 |

通过 `useMediaQuery('(max-width: 768px)')` composable 在 JS 中判断断点（用于 el-table ↔ 卡片列表双渲染等场景）。

---

## Element Plus 主题覆盖

文件：`src/assets/styles/_theme.scss`

加载顺序（`main.ts` 中严格遵守）：
1. `element-plus/dist/index.css`（EP 默认）
2. `./assets/styles/index.scss`（我们的 token + 覆盖）

同 specificity 下后加载的 `:root` 变量胜出，因此我们的覆盖全部生效。

覆盖范围：
- 主色 / 成功 / 警告 / 危险 / 错误 / 信息：全部 7 档色阶（用 `sass:color` `color.mix()` 自动计算 light-3/5/7/8/9 和 dark-2）
- 文本 / 边框 / 填充 / 背景色
- 圆角（`--el-border-radius-base: var(--r-md)`）
- 阴影
- 字号 / 字重
- Tag light 模式：改为 token 浅底 + 文本档色
- Card 边框：设为透明（由卡片变体系统自己管）

---

## P0 问题修复清单

| ID | 问题 | 修复位置 |
|---|---|---|
| P0-2 | 侧栏菜单全是 House 图标 | `AppLayout.vue` — 每个菜单项独立图标 |
| P0-3 | 首页最近记录移动端表格横滑 | `RecentInterviewRecords.vue` — 移动端改卡片列表（与历史页同款） |
| P0-4 | 语义色文字档对比度不足 | Token 系统新增 `-text` 档，全部白底 AA 以上 |
| P0-5 | 简历更新时间显示原始 ISO 字符串 | `ResumeProfilePage.vue` — `toLocaleString('zh-CN')` |
| P2-6 | 训练列表元信息冗余 | `TrainingTopicList.vue` — 清理重复 meta |

---

## 新增文件一览

| 文件 | 作用 |
|---|---|
| `src/assets/styles/_tokens.scss` | 设计 token 唯一真值源 |
| `src/assets/styles/_theme.scss` | Element Plus 主题覆盖 |
| `src/assets/styles/_cards.scss` | 卡片变体系统 |
| `src/assets/styles/_headers.scss` | 页头全局样式 |
| `src/assets/styles/tokens.ts` | token 的 JS 镜像（ECharts 用） |
| `src/components/common/PageHeader.vue` | 统一页头组件 |
| `DESIGN.md` | 本文件 |
