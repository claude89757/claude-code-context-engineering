# Claude Code Context Engineering

> Capture, analyze, and track how Claude Code constructs prompts and manages context — powered by real API traces.
>
> 捕获、分析和追踪 Claude Code 如何构建提示词与管理上下文——基于真实 API trace 数据。

## CC Trace Plugin (Core)

A Claude Code plugin that captures real API requests via [claude-trace](https://github.com/badlogic/lemmy/tree/main/apps/claude-trace), letting you see exactly what Claude Code sends to the LLM — system prompts, tools, thinking config, context management, and more. **All data comes from live traces, nothing is hardcoded.**

CC Trace 是一个 Claude Code 插件，通过 claude-trace 捕获真实 API 请求，让你看到 Claude Code 发送给 LLM 的全部内容——系统提示词、工具定义、思维配置、上下文管理等。**所有数据均来自实时抓取，没有任何硬编码。**

### Install via Plugin Marketplace / 通过插件市场安装

```bash
# 1. Add marketplace / 添加市场
/plugin marketplace add https://github.com/claude89757/claude-code-context-engineering.git

# 2. Install plugin / 安装插件
/plugin install cc-trace@claude-code-context-engineering

# 3. Use the skill / 使用技能
/cc-trace:cc-trace
```

### What it does / 功能

- **Capture traces** — One-click capture of the latest Claude Code version's API requests / 一键抓取最新版 Claude Code 的 API 请求
- **Version analysis** — Analyze any specific version from npm / 分析 npm 上任意指定版本
- **Cross-version diff** — Compare system prompts, tools, thinking config across versions / 跨版本对比系统提示词、工具、思维配置
- **Real data only** — No pre-baked knowledge; if capture fails, it tells you honestly / 纯真实数据，抓取失败如实告知

### Manual use (without plugin) / 手动使用（不安装插件）

```bash
# Clone and use scripts directly / 克隆后直接使用脚本
git clone https://github.com/claude89757/claude-code-context-engineering.git
cd claude-code-context-engineering

# Capture latest version trace / 抓取最新版本 trace
bash plugins/cc-trace/skills/cc-trace/scripts/capture-trace.sh

# Analyze a specific version / 分析指定版本
bash plugins/cc-trace/skills/cc-trace/scripts/analyze-version.sh <version>

# Compare two versions / 对比两个版本
bash plugins/cc-trace/skills/cc-trace/scripts/compare-versions.sh <v1> <v2>
```

## CC Observatory (Web Dashboard)

A self-hosted service that automatically patrols Claude Code updates, captures traces, and generates LLM-powered analysis reports through a web dashboard.

CC Observatory 是一个自托管服务，自动巡检 Claude Code 更新，捕获 trace 数据，并通过 Web 仪表盘生成 LLM 驱动的分析报告。

### Features / 功能
- **Version Timeline** — Track every Claude Code version with change history / 版本时间线
- **System Prompt Analysis** — Inspect system prompt blocks, cache strategies, and instruction hierarchy / 系统提示词分析
- **Context Engineering Insights** — Deferred tools, system reminders, message chain patterns / 上下文工程洞察
- **LLM Analysis Reports** — Auto-generated deep-dive reports on each version / LLM 深度分析报告
- **Version Diff** — Highlight what changed between versions / 版本间差异对比
- **14 Test Scenarios** — Rich scenario coverage across 5 groups / 14 个测试场景
- **Auto Patrol** — Scheduled background checks for new versions / 定时巡检

### Quick Start / 快速开始

```bash
cd cc-observatory
cp .env.example .env
# Edit .env with your LLM API key

docker compose up -d
# Access at http://localhost:9100
```

| Variable | Description | Default |
|----------|-------------|---------|
| `ANTHROPIC_AUTH_TOKEN` | API auth token | (required) |
| `ANTHROPIC_BASE_URL` | API endpoint | Tencent Cloud |
| `LLM_MODEL` | Model for reports | `kimi-k2.5` |
| `PATROL_INTERVAL_MINUTES` | Patrol interval | `30` |

## Architecture / 架构

```
├── .claude-plugin/             # Plugin marketplace definition
│   └── marketplace.json
├── plugins/cc-trace/           # CC Trace plugin (distributable)
│   ├── .claude-plugin/
│   │   └── plugin.json         # Plugin manifest
│   └── skills/cc-trace/
│       ├── SKILL.md            # Skill instructions
│       ├── scripts/            # capture, analyze, compare, prerequisites
│       └── references/         # troubleshooting, version analysis guide
├── cc-observatory/             # Self-hosted web service
│   ├── backend/                # FastAPI + SQLAlchemy + APScheduler
│   ├── frontend/               # React 19 + TypeScript + Vite + Tailwind CSS
│   ├── Dockerfile
│   └── docker-compose.yml
└── .claude-trace/              # Trace data (gitignored)
```

## Tech Stack / 技术栈

**Plugin:** Shell scripts, jq, claude-trace, npm

**Backend:** Python 3.12, FastAPI, SQLAlchemy, APScheduler

**Frontend:** React 19, TypeScript, Vite, Tailwind CSS, Recharts

**Infrastructure:** Docker, SQLite

## License

MIT
