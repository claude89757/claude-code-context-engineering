# Claude Code Context Engineering Observatory

> Monitor, analyze, and track how Claude Code's system prompts and context engineering evolve across versions.
>
> 监控、分析和追踪 Claude Code 系统提示词与上下文工程机制在各版本中的演进。

## What is this? / 这是什么？

CC Observatory is a self-hosted service that automatically patrols Claude Code updates, intercepts its API requests via [claude-trace](https://github.com/nicobailon/claude-trace), extracts structured data from the raw JSONL traces, and generates LLM-powered analysis reports — all presented through a clean web dashboard.

CC Observatory 是一个自托管服务，自动巡检 Claude Code 的更新，通过 claude-trace 拦截 API 请求，从原始 JSONL trace 中提取结构化数据，并生成 LLM 驱动的分析报告，所有内容通过 Web 仪表盘呈现。

## Features / 功能

- **Version Timeline** — Track every Claude Code version with change history / 版本时间线，追踪每个版本的变更历史
- **System Prompt Analysis** — Inspect system prompt blocks, cache strategies, and instruction hierarchy / 分析系统提示词的分块结构、缓存策略与指令层级
- **Context Engineering Insights** — Deferred tools, system reminders, message chain patterns / 延迟加载工具、System Reminders 注入、消息链模式
- **LLM Analysis Reports** — Auto-generated deep-dive reports on each version / 自动生成各版本的深度分析报告
- **Version Diff** — Highlight what changed between versions / 版本间差异对比
- **14 Test Scenarios** — Rich scenario coverage across 5 groups (basic, tools, agents, context, model) / 5 大类 14 个测试场景全面覆盖
- **Auto Patrol** — Scheduled background checks for new versions / 定时后台巡检新版本

## Quick Start / 快速开始

```bash
# Clone
git clone https://github.com/claude89757/claude-code-context-engineering.git
cd claude-code-context-engineering/cc-observatory

# Configure
cp .env.example .env
# Edit .env with your LLM API key and Claude Code auth token

# Run
docker compose up -d

# Access at http://localhost:9100
```

### Environment Variables / 环境变量

| Variable | Description | Default |
|----------|-------------|---------|
| `LLM_API_KEY` | LLM API key for analysis reports | (required) |
| `LLM_BASE_URL` | LLM API endpoint (Anthropic-compatible) | Tencent Cloud |
| `LLM_MODEL` | Model for report generation | `kimi-k2.5` |
| `CLAUDE_CODE_AUTH_TOKEN` | Claude Code auth token for trace capture | (optional) |
| `PATROL_INTERVAL_MINUTES` | Auto-patrol interval | `30` |

## Architecture / 架构

```
cc-observatory/
├── backend/          # FastAPI + SQLAlchemy + APScheduler
│   ├── routers/      # API endpoints (versions, test_runs, scenarios, reports, trends, patrol)
│   ├── services/     # Core logic (extractor, differ, scheduler, test_runner, llm_analyzer)
│   ├── scenarios/    # 14 test scenario definitions
│   └── models.py     # 7 database tables
├── frontend/         # React 19 + TypeScript + Vite + Tailwind CSS
│   └── src/pages/    # Dashboard, Timeline, VersionDetail, ScenarioDetail, PatrolStatus
├── Dockerfile        # Multi-stage build (Node.js + Python)
└── docker-compose.yml
```

## Tech Stack / 技术栈

**Backend:** Python 3.12, FastAPI, SQLAlchemy, APScheduler, claude-trace

**Frontend:** React 19, TypeScript, Vite, Tailwind CSS, Recharts, Lucide Icons

**Infrastructure:** Docker multi-stage build, SQLite

## License

MIT
