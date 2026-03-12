# CC Observatory: Claude Code 上下文工程研究平台 — 设计文档

**日期**: 2026-03-12
**状态**: 已确认

## 1. 概述

CC Observatory 是一个运行在容器中的全自动巡检服务，通过 claude-trace 拦截 Claude Code 的 API 请求，系统性研究其上下文工程（Context Engineering）机制。平台自动检测新版本、执行 14 个预设测试场景、进行结构化提取和 LLM 深度分析、生成报告，并通过 Web UI 展示所有成果。

### 1.1 定位

**上下文工程研究平台**，不是版本追踪器。重点在：
- 通过丰富测试场景观察 Claude Code 在不同情境下的上下文组装策略
- 两层分析（结构化提取 + LLM 解读）揭示"为什么这样组织上下文"
- 版本对比只是其中一个维度，核心是机制研究

### 1.2 已有同类项目对比

| 项目 | 做什么 | 缺什么 |
|------|--------|--------|
| [cchistory](https://cchistory.mariozechner.at/) | 版本 diff（Monaco 编辑器） | 只看文本差异，无场景测试，无深度分析 |
| [Piebald-AI/claude-code-system-prompts](https://github.com/Piebald-AI/claude-code-system-prompts) | 124 版本提示词归档 | 静态归档，无运行时行为观察 |
| [claude-code-changelog](https://github.com/marckrenn/claude-code-changelog) | feature flags + token 统计 | 无场景测试，无 LLM 分析 |

CC Observatory 的差异化：丰富场景测试 + 运行时行为观察 + LLM 辅助深度解读。

## 2. 系统架构

```
┌──────────────────────────────────────────────────────────────┐
│                      Docker Container                        │
│                                                              │
│  ┌─────────────┐    ┌──────────────┐    ┌────────────────┐  │
│  │  Scheduler   │───>│  Test Runner  │───>│   Analyzer     │  │
│  │ (APScheduler)│    │(claude-trace) │    │(结构化+LLM)    │  │
│  └─────────────┘    └──────┬───────┘    └───────┬────────┘  │
│                            │                     │           │
│                            v                     v           │
│                     ┌─────────────┐      ┌─────────────┐    │
│                     │   SQLite    │<─────│  Report Gen  │    │
│                     │  (数据存储)  │      │ (报告生成器)  │    │
│                     └──────┬──────┘      └─────────────┘    │
│                            │                                 │
│                            v                                 │
│                     ┌─────────────┐                          │
│                     │   FastAPI   │ :8000                     │
│                     │  (REST API) │                          │
│                     └──────┬──────┘                          │
│                            │                                 │
│                            v                                 │
│                     ┌─────────────┐                          │
│                     │   React SPA │ (build 后由 FastAPI      │
│                     │ (前端静态)   │  serve 静态文件)         │
│                     └─────────────┘                          │
└──────────────────────────────────────────────────────────────┘
```

### 2.1 核心流程

```
检测新版本 → 安装对应版本 → 执行14个测试场景 → 解析JSONL
→ 结构化提取 → 版本Diff → LLM分析 → 生成报告 → 存入数据库 → 前端展示
```

### 2.2 技术栈

| 层 | 技术 |
|---|---|
| 后端 | Python 3.12 + FastAPI + APScheduler |
| 前端 | React + TypeScript + Tailwind + shadcn/ui |
| 数据 | SQLite (SQLAlchemy) |
| 巡检引擎 | Python 子进程调 claude-trace（npm 全局安装） |
| LLM 分析 | 腾讯云 Anthropic 兼容 API (kimi-k2.5 / minimax-m2.5 / glm-5) |
| 容器 | 单 Dockerfile 多阶段构建 + docker-compose |

## 3. 测试场景（14 个）

### 3.1 基础（2 个）

| # | 场景 | 触发方式 | 观测目标 |
|---|------|---------|---------|
| 1 | 基础对话 | `"say hello"` | 系统提示词全貌、工具定义、缓存策略 |
| 2 | 文件读取 | `"读取 package.json 并总结"` | tool_result 结构、system reminders 注入 |

### 3.2 工具（4 个）

| # | 场景 | 触发方式 | 观测目标 |
|---|------|---------|---------|
| 3 | 多工具并行 | `"用 Grep 搜索 X 并用 Glob 查找 *.json"` | 并行调用消息组织 |
| 4 | 代码编辑 | `"在 test.py 添加 hello 函数"` | Edit/Write 工具、文件修改后的 reminder |
| 5 | 延迟工具加载 | `"搜索网页上关于 X 的信息"` | ToolSearch → WebSearch 延迟加载链 |
| 6 | Bash 执行 | `"运行 ls -la 并统计文件数"` | Bash 权限分类、风险评估机制 |

### 3.3 代理（3 个）

| # | 场景 | 触发方式 | 观测目标 |
|---|------|---------|---------|
| 7 | 代码库探索 | `"介绍一下这个代码库的结构"` | Explore 子代理调度、子代理系统提示词 |
| 8 | 复杂规划 | `"设计一个 REST API 服务"` | Plan 模式、TodoWrite、任务管理 |
| 9 | Skill 调用 | 触发 `/commit` 等 | Skill 提示词扩展机制 |

### 3.4 上下文管理（4 个）

| # | 场景 | 触发方式 | 观测目标 |
|---|------|---------|---------|
| 10 | /compact 压缩 | 先填充长对话再执行 `/compact` | 上下文压缩算法、信息保留策略 |
| 11 | /btw 侧边问答 | 对话中途 `/btw 问一个问题` | 无工具的纯上下文复用机制 |
| 12 | CLAUDE.md 影响 | 有/无 CLAUDE.md 对比 | CLAUDE.md 注入位置和方式 |
| 13 | /context 上下文可视化 | `/context` | 上下文使用量的计算方式 |

### 3.5 模型（1 个）

| # | 场景 | 触发方式 | 观测目标 |
|---|------|---------|---------|
| 14 | 模型切换 | `/model sonnet` 后重复场景 1 | 不同模型的提示词差异 |

## 4. 数据模型

### 4.1 versions（版本记录）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | PK | 自增 |
| version | string | "2.1.74" |
| detected_at | datetime | 检测时间 |
| npm_metadata | JSON | package.json 信息 |
| status | enum | pending/running/completed/failed |
| summary | text | LLM 生成的版本总结 |

### 4.2 test_runs（测试执行记录）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | PK | 自增 |
| version_id | FK → versions | 所属版本 |
| scenario_key | string | "basic_chat" |
| scenario_name | string | "基础对话" |
| scenario_group | string | "基础/工具/代理/上下文管理/模型" |
| status | enum | pending/running/completed/failed |
| started_at | datetime | 开始时间 |
| finished_at | datetime | 结束时间 |
| raw_jsonl | text | 原始 JSONL 内容 |
| error_message | text | 失败原因 |

### 4.3 extracted_data（结构化提取结果）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | PK | 自增 |
| test_run_id | FK → test_runs | 所属测试 |
| system_prompt | text | 完整系统提示词 |
| system_blocks | JSON | [{index, text, length, cache_control}] |
| tools | JSON | 完整工具定义 |
| tool_names | JSON | ["Agent","Bash",...] |
| deferred_tools | JSON | 延迟加载工具列表 |
| messages_chain | JSON | 消息链结构摘要 |
| api_calls | JSON | 所有 API 调用摘要 |
| system_reminders | JSON | 提取的所有 system-reminder |
| cache_strategy | JSON | 缓存配置 |
| token_usage | JSON | {input, output, cache_read, cache_create} |
| model_used | string | 使用的模型 |

### 4.4 version_diffs（版本差异）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | PK | 自增 |
| version_id | FK → versions | 新版本 |
| prev_version_id | FK → versions | 旧版本 |
| scenario_key | string | 场景 |
| diff_type | enum | system_prompt/tools/reminders/messages |
| diff_content | text | unified diff 文本 |
| change_summary | text | 变化摘要 |
| significance | enum | none/minor/major |

### 4.5 analysis_reports（LLM 分析报告）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | PK | 自增 |
| version_id | FK → versions | 所属版本 |
| report_type | enum | version_summary/scenario_deep_dive/cross_version_trend |
| title | string | 报告标题 |
| content | text | Markdown 格式的分析报告 |
| model_used | string | "kimi-k2.5" 等 |
| generated_at | datetime | 生成时间 |
| token_cost | JSON | {input, output} |

## 5. 后端 API

```
GET  /api/versions                         # 版本列表（分页、筛选）
GET  /api/versions/latest                  # 最新版本
GET  /api/versions/{id}                    # 版本详情（含 LLM 分析报告）
GET  /api/versions/{id}/diff               # 版本与上一版本的差异汇总

GET  /api/test-runs?version_id=&scenario_key=  # 测试运行记录
GET  /api/test-runs/{id}                   # 单次测试详情
GET  /api/test-runs/{id}/raw               # 原始 JSONL 数据
GET  /api/test-runs/{id}/diff              # 与上一版本同场景的 diff

GET  /api/scenarios                        # 场景列表
GET  /api/scenarios/{key}/history          # 某场景跨版本历史

GET  /api/reports?version_id=&type=        # 分析报告列表
GET  /api/reports/{id}                     # 报告详情

GET  /api/trends                           # 趋势数据
     ?metric=system_prompt_length|tool_count|token_usage
     &from_version=&to_version=

GET  /api/patrol/status                    # 巡检状态
GET  /api/patrol/history                   # 巡检历史
POST /api/patrol/trigger                   # 手动触发巡检

GET  /api/health                           # 健康检查
```

## 6. 前端页面

### 6.1 页面层级

```
首页（总览仪表盘）
├── 时间线视图（版本演进时间线）
│   └── 版本详情页
│       ├── 版本变更摘要（LLM 分析报告）
│       ├── 场景测试结果列表
│       │   └── 场景详情页
│       │       ├── 原始 API 请求/响应查看器
│       │       ├── 系统提示词查看器（分 block 高亮）
│       │       ├── 消息链可视化
│       │       ├── 工具定义查看器
│       │       └── 与上一版本的 Diff 视图
│       └── 版本间对比（side-by-side diff）
├── 场景维度视图（按场景分组，看同一场景跨版本变化）
└── 巡检状态页（当前运行状态、历史执行日志）
```

### 6.2 首页仪表盘

- 指标卡片：已追踪版本数、最新版本、上次巡检时间、发现变更数
- 最近版本变更列表：每个版本的 LLM 摘要 + 变更级别（红/黄/绿）
- 上下文工程趋势图：系统提示词长度、工具数量、token 消耗的折线图

### 6.3 版本详情页

- 顶部：LLM 生成的版本分析报告（Markdown 渲染）
- 下方：14 个场景的卡片网格，显示关键指标和变化标识

### 6.4 场景详情页（核心页面）

多 Tab 布局：
- **概览**: API 调用流程图
- **系统提示词**: 分 block 展示，每个章节可折叠
- **消息链**: 消息结构可视化
- **工具定义**: 工具列表及参数详情
- **Diff**: Monaco Diff Editor（与上一版本对比）
- **原始数据**: JSONL 查看器

### 6.5 场景维度视图

选择一个场景，查看该场景在所有版本中的关键指标变化趋势。

### 6.6 巡检状态页

实时显示巡检任务运行状态、历史执行记录、失败日志。

## 7. 项目结构

```
cc-observatory/
├── docker-compose.yml
├── Dockerfile
├── backend/
│   ├── requirements.txt
│   ├── main.py
│   ├── config.py
│   ├── database.py
│   ├── models.py
│   ├── routers/
│   │   ├── versions.py
│   │   ├── test_runs.py
│   │   ├── scenarios.py
│   │   ├── reports.py
│   │   ├── trends.py
│   │   └── patrol.py
│   ├── services/
│   │   ├── scheduler.py
│   │   ├── version_checker.py
│   │   ├── test_runner.py
│   │   ├── extractor.py
│   │   ├── differ.py
│   │   └── llm_analyzer.py
│   ├── scenarios/
│   │   ├── __init__.py
│   │   └── setup.py
│   └── data/
│       ├── observatory.db
│       └── traces/
├── frontend/
│   ├── package.json
│   ├── vite.config.ts
│   ├── src/
│   │   ├── pages/
│   │   │   ├── Dashboard.tsx
│   │   │   ├── Timeline.tsx
│   │   │   ├── VersionDetail.tsx
│   │   │   ├── ScenarioDetail.tsx
│   │   │   ├── ScenarioHistory.tsx
│   │   │   └── PatrolStatus.tsx
│   │   ├── components/
│   │   │   ├── SystemPromptViewer.tsx
│   │   │   ├── MessageChainViz.tsx
│   │   │   ├── DiffViewer.tsx
│   │   │   ├── ToolsViewer.tsx
│   │   │   ├── TrendChart.tsx
│   │   │   ├── VersionCard.tsx
│   │   │   └── ApiCallFlow.tsx
│   │   ├── hooks/
│   │   └── lib/
│   └── dist/
└── scripts/
    └── init_db.py
```

## 8. 容器化

### Dockerfile

多阶段构建：
1. Stage 1: Node.js 构建前端
2. Stage 2: Python 运行时 + 安装 Node.js（给 claude-trace）+ 复制前端产物

### docker-compose.yml

- 单服务，端口 8000
- Volume 持久化数据
- 环境变量：LLM API Key/URL/Model、巡检间隔、Claude Code Auth Token

### 关键注意点

1. 容器中运行 claude-trace 需要 Claude Code 的 OAuth token（通过 `claude-trace --extract-token` 提取）
2. SQLite 和 JSONL 通过 Docker volume 持久化
3. 前端 build 后由 FastAPI serve 静态文件，单容器单端口

## 9. LLM 分析配置

- Base URL: `https://api.lkeap.cloud.tencent.com/coding/anthropic`
- API Key: 通过环境变量配置
- 可用模型: minimax-m2.5, glm-5, kimi-k2.5
- Anthropic 兼容协议，使用 `/v1/messages` 接口
