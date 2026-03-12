# CC Observatory Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a containerized auto-patrol service that studies Claude Code's context engineering by running 14 test scenarios via claude-trace, extracting structured data, computing version diffs, generating LLM analysis reports, and presenting everything through a React SPA.

**Architecture:** FastAPI backend with APScheduler for auto-patrol, SQLite for storage, claude-trace (npm) for API interception. React + Tailwind + shadcn/ui frontend served as static files by FastAPI. Single Docker container with both Python and Node.js runtimes.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy, APScheduler, httpx | React 18, TypeScript, Vite, Tailwind CSS, shadcn/ui, recharts, @monaco-editor/react | SQLite | Docker

**Design doc:** `docs/plans/2026-03-12-cc-observatory-design.md`

---

## Phase 1: Project Scaffolding & Database

### Task 1: Initialize backend project

**Files:**
- Create: `cc-observatory/backend/requirements.txt`
- Create: `cc-observatory/backend/config.py`
- Create: `cc-observatory/backend/main.py`

**Step 1: Create project directory and requirements.txt**

```bash
mkdir -p cc-observatory/backend/routers cc-observatory/backend/services cc-observatory/backend/scenarios cc-observatory/backend/data/traces
```

`cc-observatory/backend/requirements.txt`:
```
fastapi==0.115.6
uvicorn[standard]==0.34.0
sqlalchemy==2.0.36
apscheduler==3.10.4
httpx==0.28.1
pydantic==2.10.4
python-dotenv==1.0.1
```

**Step 2: Create config.py**

`cc-observatory/backend/config.py`:
```python
import os
from pathlib import Path

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
TRACES_DIR = DATA_DIR / "traces"
DB_PATH = DATA_DIR / "observatory.db"

LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.lkeap.cloud.tencent.com/coding/anthropic")
LLM_MODEL = os.getenv("LLM_MODEL", "kimi-k2.5")
PATROL_INTERVAL_MINUTES = int(os.getenv("PATROL_INTERVAL_MINUTES", "30"))
CLAUDE_CODE_AUTH_TOKEN = os.getenv("CLAUDE_CODE_AUTH_TOKEN", "")
```

**Step 3: Create minimal FastAPI main.py**

`cc-observatory/backend/main.py`:
```python
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pathlib import Path

app = FastAPI(title="CC Observatory", version="0.1.0")

@app.get("/api/health")
def health():
    return {"status": "ok"}

# Serve frontend static files (added after frontend build)
frontend_dist = Path(__file__).parent.parent / "frontend" / "dist"
if frontend_dist.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="frontend")
```

**Step 4: Verify backend starts**

Run: `cd cc-observatory && pip install -r backend/requirements.txt && uvicorn backend.main:app --port 8000`
Expected: Server starts, `curl localhost:8000/api/health` returns `{"status":"ok"}`

**Step 5: Commit**

```bash
git add cc-observatory/
git commit -m "feat: initialize backend project scaffolding"
```

---

### Task 2: Database models and initialization

**Files:**
- Create: `cc-observatory/backend/database.py`
- Create: `cc-observatory/backend/models.py`

**Step 1: Create database.py with SQLAlchemy engine and session**

`cc-observatory/backend/database.py`:
```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from backend.config import DB_PATH

engine = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)

class Base(DeclarativeBase):
    pass

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(bind=engine)
```

**Step 2: Create models.py with all 5 tables**

`cc-observatory/backend/models.py`:
```python
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON, Enum as SAEnum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from backend.database import Base

class VersionStatus(str, enum.Enum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"

class RunStatus(str, enum.Enum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"

class DiffType(str, enum.Enum):
    system_prompt = "system_prompt"
    tools = "tools"
    reminders = "reminders"
    messages = "messages"

class Significance(str, enum.Enum):
    none = "none"
    minor = "minor"
    major = "major"

class ReportType(str, enum.Enum):
    version_summary = "version_summary"
    scenario_deep_dive = "scenario_deep_dive"
    cross_version_trend = "cross_version_trend"

class Version(Base):
    __tablename__ = "versions"
    id = Column(Integer, primary_key=True)
    version = Column(String, unique=True, nullable=False)
    detected_at = Column(DateTime, default=datetime.utcnow)
    npm_metadata = Column(JSON)
    status = Column(String, default=VersionStatus.pending)
    summary = Column(Text)
    test_runs = relationship("TestRun", back_populates="version")
    reports = relationship("AnalysisReport", back_populates="version")

class TestRun(Base):
    __tablename__ = "test_runs"
    id = Column(Integer, primary_key=True)
    version_id = Column(Integer, ForeignKey("versions.id"), nullable=False)
    scenario_key = Column(String, nullable=False)
    scenario_name = Column(String)
    scenario_group = Column(String)
    status = Column(String, default=RunStatus.pending)
    started_at = Column(DateTime)
    finished_at = Column(DateTime)
    raw_jsonl = Column(Text)
    error_message = Column(Text)
    version = relationship("Version", back_populates="test_runs")
    extracted = relationship("ExtractedData", back_populates="test_run", uselist=False)

class ExtractedData(Base):
    __tablename__ = "extracted_data"
    id = Column(Integer, primary_key=True)
    test_run_id = Column(Integer, ForeignKey("test_runs.id"), nullable=False)
    system_prompt = Column(Text)
    system_blocks = Column(JSON)
    tools = Column(JSON)
    tool_names = Column(JSON)
    deferred_tools = Column(JSON)
    messages_chain = Column(JSON)
    api_calls = Column(JSON)
    system_reminders = Column(JSON)
    cache_strategy = Column(JSON)
    token_usage = Column(JSON)
    model_used = Column(String)
    test_run = relationship("TestRun", back_populates="extracted")

class VersionDiff(Base):
    __tablename__ = "version_diffs"
    id = Column(Integer, primary_key=True)
    version_id = Column(Integer, ForeignKey("versions.id"), nullable=False)
    prev_version_id = Column(Integer, ForeignKey("versions.id"), nullable=False)
    scenario_key = Column(String)
    diff_type = Column(String)
    diff_content = Column(Text)
    change_summary = Column(Text)
    significance = Column(String, default=Significance.none)

class AnalysisReport(Base):
    __tablename__ = "analysis_reports"
    id = Column(Integer, primary_key=True)
    version_id = Column(Integer, ForeignKey("versions.id"), nullable=False)
    report_type = Column(String)
    title = Column(String)
    content = Column(Text)
    model_used = Column(String)
    generated_at = Column(DateTime, default=datetime.utcnow)
    token_cost = Column(JSON)
    version = relationship("Version", back_populates="reports")
```

**Step 3: Add init_db call to main.py startup**

Add to `cc-observatory/backend/main.py`:
```python
from contextlib import asynccontextmanager
from backend.database import init_db

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(title="CC Observatory", version="0.1.0", lifespan=lifespan)
```

**Step 4: Verify database creates correctly**

Run: `cd cc-observatory && python -c "from backend.database import init_db; init_db(); print('OK')"`
Expected: `OK` printed, `backend/data/observatory.db` file created

**Step 5: Commit**

```bash
git add cc-observatory/backend/database.py cc-observatory/backend/models.py cc-observatory/backend/main.py
git commit -m "feat: add SQLAlchemy models for all 5 tables"
```

---

## Phase 2: Core Backend Services

### Task 3: Version checker service

**Files:**
- Create: `cc-observatory/backend/services/version_checker.py`
- Create: `cc-observatory/tests/test_version_checker.py`

**Step 1: Write the test**

`cc-observatory/tests/test_version_checker.py`:
```python
import pytest
from unittest.mock import patch, MagicMock
from backend.services.version_checker import get_all_npm_versions, get_latest_npm_version

def test_parse_npm_versions():
    """Test parsing npm version output."""
    mock_result = MagicMock()
    mock_result.stdout = '["2.1.72","2.1.73","2.1.74"]'
    mock_result.returncode = 0
    with patch("subprocess.run", return_value=mock_result):
        versions = get_all_npm_versions()
        assert versions == ["2.1.72", "2.1.73", "2.1.74"]

def test_get_latest():
    mock_result = MagicMock()
    mock_result.stdout = '["2.1.72","2.1.73","2.1.74"]'
    mock_result.returncode = 0
    with patch("subprocess.run", return_value=mock_result):
        latest = get_latest_npm_version()
        assert latest == "2.1.74"
```

**Step 2: Run test to verify it fails**

Run: `cd cc-observatory && python -m pytest tests/test_version_checker.py -v`
Expected: FAIL (module not found)

**Step 3: Implement version_checker.py**

`cc-observatory/backend/services/version_checker.py`:
```python
import subprocess
import json
from typing import Optional

PACKAGE_NAME = "@anthropic-ai/claude-code"

def get_all_npm_versions() -> list[str]:
    result = subprocess.run(
        ["npm", "view", PACKAGE_NAME, "versions", "--json"],
        capture_output=True, text=True, timeout=30
    )
    if result.returncode != 0:
        raise RuntimeError(f"npm view failed: {result.stderr}")
    return json.loads(result.stdout)

def get_latest_npm_version() -> str:
    versions = get_all_npm_versions()
    return versions[-1]

def get_npm_metadata(version: str) -> dict:
    result = subprocess.run(
        ["npm", "view", f"{PACKAGE_NAME}@{version}", "--json"],
        capture_output=True, text=True, timeout=30
    )
    if result.returncode != 0:
        raise RuntimeError(f"npm view failed: {result.stderr}")
    return json.loads(result.stdout)

def install_claude_code_version(version: str, target_dir: str) -> str:
    """Install a specific version of claude-code to target_dir. Returns path to cli.js."""
    result = subprocess.run(
        ["npm", "install", f"{PACKAGE_NAME}@{version}", "--prefix", target_dir],
        capture_output=True, text=True, timeout=120
    )
    if result.returncode != 0:
        raise RuntimeError(f"npm install failed: {result.stderr}")
    return f"{target_dir}/node_modules/@anthropic-ai/claude-code/cli.js"
```

**Step 4: Run test to verify it passes**

Run: `cd cc-observatory && python -m pytest tests/test_version_checker.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add cc-observatory/backend/services/version_checker.py cc-observatory/tests/
git commit -m "feat: add version checker service for npm version detection"
```

---

### Task 4: Test runner service (claude-trace executor)

**Files:**
- Create: `cc-observatory/backend/services/test_runner.py`
- Create: `cc-observatory/backend/scenarios/__init__.py`

**Step 1: Create scenario definitions**

`cc-observatory/backend/scenarios/__init__.py`:
```python
SCENARIOS = [
    {
        "key": "basic_chat",
        "name": "基础对话",
        "group": "基础",
        "prompt": "say hello",
        "mode": "single_prompt",
        "description": "捕获基础系统提示词、工具定义、缓存策略"
    },
    {
        "key": "file_read",
        "name": "文件读取",
        "group": "基础",
        "prompt": "读取 package.json 并总结内容",
        "mode": "single_prompt",
        "description": "观测 Read tool_result 和 system reminders 注入"
    },
    {
        "key": "multi_tool_parallel",
        "name": "多工具并行",
        "group": "工具",
        "prompt": "用 Grep 搜索包含 claude 的文件，同时用 Glob 查找所有 .json 文件",
        "mode": "single_prompt",
        "description": "观测并行工具调用的消息组织方式"
    },
    {
        "key": "code_edit",
        "name": "代码编辑",
        "group": "工具",
        "prompt": "创建一个 test_hello.py 文件，包含一个 hello 函数，返回 'Hello, World!'",
        "mode": "single_prompt",
        "description": "观测 Edit/Write 工具和文件修改后的 system reminder"
    },
    {
        "key": "deferred_tool_load",
        "name": "延迟工具加载",
        "group": "工具",
        "prompt": "使用 WebSearch 搜索 Python 3.12 的新特性",
        "mode": "single_prompt",
        "description": "观测 ToolSearch → WebSearch 的延迟加载链"
    },
    {
        "key": "bash_exec",
        "name": "Bash 执行",
        "group": "工具",
        "prompt": "运行 ls -la 命令并统计当前目录下有多少个文件",
        "mode": "single_prompt",
        "description": "观测 Bash 工具权限分类和风险评估机制"
    },
    {
        "key": "codebase_explore",
        "name": "代码库探索",
        "group": "代理",
        "prompt": "详细介绍一下这个代码库的结构和主要功能",
        "mode": "single_prompt",
        "description": "观测 Explore 子代理调度和子代理系统提示词"
    },
    {
        "key": "complex_planning",
        "name": "复杂规划",
        "group": "代理",
        "prompt": "设计一个简单的 REST API 服务，支持用户注册和登录，给出实现计划",
        "mode": "single_prompt",
        "description": "观测 Plan 模式、TodoWrite、任务管理上下文"
    },
    {
        "key": "skill_invoke",
        "name": "Skill 调用",
        "group": "代理",
        "prompt": "请帮我执行 /help 命令",
        "mode": "single_prompt",
        "description": "观测 Skill 系统的提示词扩展机制"
    },
    {
        "key": "compact_compression",
        "name": "/compact 压缩",
        "group": "上下文管理",
        "prompt": "请详细解释 Python 的 asyncio 模块，包括事件循环、协程、Future 和 Task 的概念",
        "mode": "multi_turn",
        "turns": [
            "请详细解释 Python 的 asyncio 模块，包括事件循环、协程、Future 和 Task 的概念",
            "继续解释 asyncio 的高级用法，包括信号量、队列和子进程",
            "/compact"
        ],
        "description": "观测上下文压缩算法和信息保留策略"
    },
    {
        "key": "btw_side_query",
        "name": "/btw 侧边问答",
        "group": "上下文管理",
        "prompt": "读取 package.json",
        "mode": "multi_turn",
        "turns": [
            "读取 package.json 并分析依赖",
            "/btw 顺便问一下，Python 的 GIL 是什么？"
        ],
        "description": "观测无工具的纯上下文复用机制"
    },
    {
        "key": "claude_md_impact",
        "name": "CLAUDE.md 影响",
        "group": "上下文管理",
        "prompt": "say hello",
        "mode": "paired",
        "setup_variants": ["without_claude_md", "with_claude_md"],
        "description": "对比有无 CLAUDE.md 时的上下文注入差异"
    },
    {
        "key": "context_visualization",
        "name": "/context 上下文可视化",
        "group": "上下文管理",
        "prompt": "say hello",
        "mode": "multi_turn",
        "turns": ["say hello", "/context"],
        "description": "观测上下文使用量的计算方式"
    },
    {
        "key": "model_switch",
        "name": "模型切换",
        "group": "模型",
        "prompt": "say hello",
        "mode": "multi_turn",
        "turns": ["/model sonnet", "say hello"],
        "description": "观测不同模型的提示词差异"
    },
]

SCENARIO_MAP = {s["key"]: s for s in SCENARIOS}
```

**Step 2: Create test_runner.py**

`cc-observatory/backend/services/test_runner.py`:
```python
import subprocess
import json
import os
import tempfile
from pathlib import Path
from datetime import datetime
from typing import Optional

from backend.config import TRACES_DIR

def run_single_prompt_scenario(
    claude_cli_path: str,
    prompt: str,
    scenario_key: str,
    version: str,
) -> dict:
    """Run claude-trace with a single -p prompt. Returns dict with jsonl_path and raw content."""
    TRACES_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    log_name = f"{version}_{scenario_key}_{timestamp}"
    trace_dir = TRACES_DIR / f"{version}"
    trace_dir.mkdir(parents=True, exist_ok=True)

    # Ensure .claude-trace subdirectory exists (claude-trace writes logs there)
    claude_trace_dir = trace_dir / ".claude-trace"
    claude_trace_dir.mkdir(parents=True, exist_ok=True)

    env = {**os.environ}
    env.pop("CLAUDECODE", None)  # Prevent nested session error

    cmd = [
        "claude-trace",
        "--include-all-requests",
        "--no-open",
        "--claude-path", claude_cli_path,
        "--log", log_name,
        "--run-with",
        "-p", prompt,
        "--output-format", "json",
    ]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=300,
        cwd=str(trace_dir),
        env=env,
    )

    # Find the generated JSONL file
    jsonl_path = claude_trace_dir / f"{log_name}.jsonl"
    if not jsonl_path.exists():
        return {
            "success": False,
            "error": result.stderr or result.stdout or "JSONL file not generated",
            "raw_jsonl": None,
            "jsonl_path": None,
        }

    raw_jsonl = jsonl_path.read_text()

    return {
        "success": True,
        "error": None,
        "raw_jsonl": raw_jsonl,
        "jsonl_path": str(jsonl_path),
    }

def run_multi_turn_scenario(
    claude_cli_path: str,
    turns: list[str],
    scenario_key: str,
    version: str,
) -> dict:
    """Run claude-trace with multi-turn conversation using --resume or piped input.
    For slash commands (/compact, /btw, /context, /model), uses interactive mode with piped stdin.
    """
    TRACES_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    log_name = f"{version}_{scenario_key}_{timestamp}"
    trace_dir = TRACES_DIR / f"{version}"
    trace_dir.mkdir(parents=True, exist_ok=True)
    claude_trace_dir = trace_dir / ".claude-trace"
    claude_trace_dir.mkdir(parents=True, exist_ok=True)

    env = {**os.environ}
    env.pop("CLAUDECODE", None)

    # Join turns with newlines and pipe to stdin
    stdin_input = "\n".join(turns) + "\n/exit\n"

    cmd = [
        "claude-trace",
        "--include-all-requests",
        "--no-open",
        "--claude-path", claude_cli_path,
        "--log", log_name,
    ]

    result = subprocess.run(
        cmd,
        input=stdin_input,
        capture_output=True,
        text=True,
        timeout=600,
        cwd=str(trace_dir),
        env=env,
    )

    jsonl_path = claude_trace_dir / f"{log_name}.jsonl"
    if not jsonl_path.exists():
        return {
            "success": False,
            "error": result.stderr or result.stdout or "JSONL file not generated",
            "raw_jsonl": None,
            "jsonl_path": None,
        }

    return {
        "success": True,
        "error": None,
        "raw_jsonl": jsonl_path.read_text(),
        "jsonl_path": str(jsonl_path),
    }
```

**Step 3: Commit**

```bash
git add cc-observatory/backend/scenarios/ cc-observatory/backend/services/test_runner.py
git commit -m "feat: add 14 test scenarios and claude-trace test runner"
```

---

### Task 5: JSONL extractor service

**Files:**
- Create: `cc-observatory/backend/services/extractor.py`
- Create: `cc-observatory/tests/test_extractor.py`

**Step 1: Write the test using existing JSONL from our earlier trace**

`cc-observatory/tests/test_extractor.py`:
```python
import json
import pytest
from backend.services.extractor import extract_from_jsonl

SAMPLE_ENTRY = {
    "request": {
        "url": "https://api.anthropic.com/v1/messages?beta=true",
        "method": "POST",
        "body": {
            "model": "claude-opus-4-6",
            "system": [
                {"type": "text", "text": "billing header"},
                {"type": "text", "text": "identity", "cache_control": {"type": "ephemeral", "ttl": "1h"}},
                {"type": "text", "text": "core instructions here " * 100, "cache_control": {"type": "ephemeral", "ttl": "1h"}},
            ],
            "messages": [
                {"role": "user", "content": "<available-deferred-tools>\nWebFetch\nWebSearch\n</available-deferred-tools>"},
                {"role": "user", "content": [
                    {"type": "text", "text": "<system-reminder>reminder1</system-reminder>"},
                    {"type": "text", "text": "say hello"},
                ]},
            ],
            "tools": [
                {"name": "Bash", "description": "exec bash"},
                {"name": "Read", "description": "read files"},
            ],
            "max_tokens": 16000,
        }
    },
    "response": {"status": 200}
}

def make_jsonl(*entries):
    return "\n".join(json.dumps(e) for e in entries)

def test_extract_system_prompt():
    jsonl = make_jsonl(SAMPLE_ENTRY)
    result = extract_from_jsonl(jsonl)
    assert len(result["system_blocks"]) == 3
    assert result["system_blocks"][1]["cache_control"] == {"type": "ephemeral", "ttl": "1h"}

def test_extract_tools():
    jsonl = make_jsonl(SAMPLE_ENTRY)
    result = extract_from_jsonl(jsonl)
    assert result["tool_names"] == ["Bash", "Read"]

def test_extract_deferred_tools():
    jsonl = make_jsonl(SAMPLE_ENTRY)
    result = extract_from_jsonl(jsonl)
    assert "WebFetch" in result["deferred_tools"]

def test_extract_system_reminders():
    jsonl = make_jsonl(SAMPLE_ENTRY)
    result = extract_from_jsonl(jsonl)
    assert any("reminder1" in r for r in result["system_reminders"])

def test_extract_model():
    jsonl = make_jsonl(SAMPLE_ENTRY)
    result = extract_from_jsonl(jsonl)
    assert result["model_used"] == "claude-opus-4-6"
```

**Step 2: Run test to verify it fails**

Run: `cd cc-observatory && python -m pytest tests/test_extractor.py -v`
Expected: FAIL

**Step 3: Implement extractor.py**

`cc-observatory/backend/services/extractor.py`:
```python
import json
import re
from typing import Any

def extract_from_jsonl(raw_jsonl: str) -> dict:
    """Parse JSONL from claude-trace and extract structured context engineering data."""
    entries = [json.loads(line) for line in raw_jsonl.strip().split("\n") if line.strip()]

    result = {
        "system_prompt": "",
        "system_blocks": [],
        "tools": [],
        "tool_names": [],
        "deferred_tools": [],
        "messages_chain": [],
        "api_calls": [],
        "system_reminders": [],
        "cache_strategy": [],
        "token_usage": {},
        "model_used": "",
    }

    for entry in entries:
        req = entry.get("request", {})
        url = req.get("url", "")
        method = req.get("method", "")

        result["api_calls"].append({
            "method": method,
            "url": url,
        })

        if "/v1/messages" not in url:
            continue

        body = req.get("body", {})
        if isinstance(body, str):
            body = json.loads(body)

        # Only process the first /v1/messages call for base data
        if not result["model_used"]:
            result["model_used"] = body.get("model", "")

            # System prompt blocks
            system = body.get("system", [])
            if isinstance(system, list):
                full_text_parts = []
                for i, block in enumerate(system):
                    if isinstance(block, dict):
                        text = block.get("text", "")
                        full_text_parts.append(text)
                        result["system_blocks"].append({
                            "index": i,
                            "length": len(text),
                            "cache_control": block.get("cache_control"),
                            "text": text,
                        })
                result["system_prompt"] = "\n\n".join(full_text_parts)

            # Tools
            tools = body.get("tools", [])
            result["tools"] = tools
            result["tool_names"] = [t.get("name", "") for t in tools]

            # Cache strategy
            result["cache_strategy"] = [
                {"block_index": b["index"], "cache_control": b["cache_control"]}
                for b in result["system_blocks"]
                if b["cache_control"]
            ]

        # Extract from all /v1/messages calls
        messages = body.get("messages", [])
        turn_summary = []
        for msg in messages:
            role = msg.get("role", "")
            content = msg.get("content", "")
            if isinstance(content, str):
                # Check for deferred tools
                dt_match = re.findall(r"<available-deferred-tools>\n(.*?)</available-deferred-tools>", content, re.DOTALL)
                if dt_match:
                    result["deferred_tools"] = [t.strip() for t in dt_match[0].strip().split("\n") if t.strip()]

                # Check for system reminders
                sr_matches = re.findall(r"<system-reminder>(.*?)</system-reminder>", content, re.DOTALL)
                result["system_reminders"].extend(sr_matches)

                turn_summary.append({"role": role, "type": "text", "length": len(content)})
            elif isinstance(content, list):
                block_types = []
                for block in content:
                    btype = block.get("type", "unknown")
                    if btype == "text":
                        text = block.get("text", "")
                        sr_matches = re.findall(r"<system-reminder>(.*?)</system-reminder>", text, re.DOTALL)
                        result["system_reminders"].extend(sr_matches)
                    elif btype == "tool_use":
                        btype = f"tool_use({block.get('name', '')})"
                    block_types.append(btype)
                turn_summary.append({"role": role, "types": block_types})

        result["messages_chain"].append({
            "num_messages": len(messages),
            "summary": turn_summary,
        })

        # Token usage from response (if available)
        resp = entry.get("response", {})
        usage = resp.get("usage", {})
        if usage:
            result["token_usage"] = usage

    # Deduplicate system reminders
    result["system_reminders"] = list(dict.fromkeys(result["system_reminders"]))

    return result
```

**Step 4: Run test to verify it passes**

Run: `cd cc-observatory && python -m pytest tests/test_extractor.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add cc-observatory/backend/services/extractor.py cc-observatory/tests/test_extractor.py
git commit -m "feat: add JSONL extractor for structured context engineering data"
```

---

### Task 6: Diff computation service

**Files:**
- Create: `cc-observatory/backend/services/differ.py`
- Create: `cc-observatory/tests/test_differ.py`

**Step 1: Write the test**

`cc-observatory/tests/test_differ.py`:
```python
from backend.services.differ import compute_text_diff, compute_list_diff, classify_significance

def test_text_diff_detects_addition():
    old = "line1\nline2\nline3"
    new = "line1\nline2\nnew line\nline3"
    diff = compute_text_diff(old, new)
    assert "+new line" in diff

def test_text_diff_no_change():
    text = "line1\nline2"
    diff = compute_text_diff(text, text)
    assert diff == ""

def test_list_diff():
    old = ["Bash", "Read", "Write"]
    new = ["Bash", "Read", "Write", "Agent"]
    added, removed = compute_list_diff(old, new)
    assert added == ["Agent"]
    assert removed == []

def test_significance_major():
    assert classify_significance(diff_lines=50, total_lines=100) == "major"

def test_significance_minor():
    assert classify_significance(diff_lines=3, total_lines=100) == "minor"

def test_significance_none():
    assert classify_significance(diff_lines=0, total_lines=100) == "none"
```

**Step 2: Run test to verify it fails**

Run: `cd cc-observatory && python -m pytest tests/test_differ.py -v`
Expected: FAIL

**Step 3: Implement differ.py**

`cc-observatory/backend/services/differ.py`:
```python
import difflib

def compute_text_diff(old_text: str, new_text: str) -> str:
    """Compute unified diff between two texts. Returns empty string if identical."""
    if old_text == new_text:
        return ""
    old_lines = old_text.splitlines(keepends=True)
    new_lines = new_text.splitlines(keepends=True)
    diff = difflib.unified_diff(old_lines, new_lines, fromfile="old", tofile="new")
    return "".join(diff)

def compute_list_diff(old_list: list, new_list: list) -> tuple[list, list]:
    """Return (added, removed) items between two lists."""
    old_set = set(old_list)
    new_set = set(new_list)
    added = sorted(new_set - old_set)
    removed = sorted(old_set - new_set)
    return added, removed

def classify_significance(diff_lines: int, total_lines: int) -> str:
    """Classify change significance based on diff size relative to total."""
    if diff_lines == 0:
        return "none"
    ratio = diff_lines / max(total_lines, 1)
    if ratio > 0.1 or diff_lines > 20:
        return "major"
    return "minor"

def compute_version_diffs(old_extracted: dict, new_extracted: dict) -> list[dict]:
    """Compute all diffs between two extracted data sets. Returns list of diff records."""
    diffs = []

    # System prompt diff
    sp_diff = compute_text_diff(
        old_extracted.get("system_prompt", ""),
        new_extracted.get("system_prompt", "")
    )
    if sp_diff:
        diff_line_count = len([l for l in sp_diff.split("\n") if l.startswith("+") or l.startswith("-")])
        total_lines = len(new_extracted.get("system_prompt", "").split("\n"))
        diffs.append({
            "diff_type": "system_prompt",
            "diff_content": sp_diff,
            "change_summary": f"System prompt changed ({diff_line_count} lines affected)",
            "significance": classify_significance(diff_line_count, total_lines),
        })

    # Tools diff
    old_tools = old_extracted.get("tool_names", [])
    new_tools = new_extracted.get("tool_names", [])
    added, removed = compute_list_diff(old_tools, new_tools)
    if added or removed:
        summary_parts = []
        if added:
            summary_parts.append(f"Added: {', '.join(added)}")
        if removed:
            summary_parts.append(f"Removed: {', '.join(removed)}")
        diffs.append({
            "diff_type": "tools",
            "diff_content": f"Added: {added}\nRemoved: {removed}",
            "change_summary": "; ".join(summary_parts),
            "significance": "major" if len(added) + len(removed) > 2 else "minor",
        })

    # System reminders diff
    old_reminders = old_extracted.get("system_reminders", [])
    new_reminders = new_extracted.get("system_reminders", [])
    sr_added, sr_removed = compute_list_diff(old_reminders, new_reminders)
    if sr_added or sr_removed:
        diffs.append({
            "diff_type": "reminders",
            "diff_content": f"Added: {len(sr_added)}\nRemoved: {len(sr_removed)}",
            "change_summary": f"System reminders changed: +{len(sr_added)} -{len(sr_removed)}",
            "significance": "minor",
        })

    return diffs
```

**Step 4: Run test to verify it passes**

Run: `cd cc-observatory && python -m pytest tests/test_differ.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add cc-observatory/backend/services/differ.py cc-observatory/tests/test_differ.py
git commit -m "feat: add diff computation service for version comparison"
```

---

### Task 7: LLM analyzer service

**Files:**
- Create: `cc-observatory/backend/services/llm_analyzer.py`

**Step 1: Implement llm_analyzer.py**

`cc-observatory/backend/services/llm_analyzer.py`:
```python
import httpx
import json
from backend.config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL

async def call_llm(prompt: str, model: str = None) -> dict:
    """Call LLM via Anthropic-compatible API. Returns {content, model_used, token_cost}."""
    model = model or LLM_MODEL
    async with httpx.AsyncClient(timeout=120) as client:
        response = await client.post(
            f"{LLM_BASE_URL}/v1/messages",
            headers={
                "x-api-key": LLM_API_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": model,
                "max_tokens": 4096,
                "messages": [{"role": "user", "content": prompt}],
            },
        )
        response.raise_for_status()
        data = response.json()

    content = ""
    if "content" in data and isinstance(data["content"], list):
        content = "\n".join(
            block.get("text", "") for block in data["content"] if block.get("type") == "text"
        )

    usage = data.get("usage", {})
    return {
        "content": content,
        "model_used": model,
        "token_cost": {
            "input": usage.get("input_tokens", 0),
            "output": usage.get("output_tokens", 0),
        },
    }

async def generate_version_report(version: str, diffs: list[dict], extracted_samples: list[dict]) -> dict:
    """Generate LLM analysis report for a version's changes."""
    diff_text = ""
    for d in diffs:
        diff_text += f"\n### {d['diff_type']} ({d['significance']})\n{d['change_summary']}\n```\n{d['diff_content'][:2000]}\n```\n"

    # Include a sample of extracted data for context
    context_info = ""
    for sample in extracted_samples[:3]:
        context_info += f"\n场景: {sample.get('scenario_key', '')}\n"
        context_info += f"模型: {sample.get('model_used', '')}\n"
        context_info += f"系统提示词长度: {len(sample.get('system_prompt', ''))} chars\n"
        context_info += f"工具数: {len(sample.get('tool_names', []))}\n"
        context_info += f"工具列表: {sample.get('tool_names', [])}\n"

    prompt = f"""你是一个 AI 系统分析专家。以下是 Claude Code v{version} 与上一版本的差异数据。
请用中文撰写一份深度分析报告，包含：

1. **变更概述** — 本次版本的主要变化点
2. **上下文工程分析** — 这些变化反映了怎样的上下文组织策略演进
3. **意图推测** — Anthropic 可能的设计意图和动机
4. **影响评估** — 这些变化对使用者体验和 AI 行为的可能影响
5. **趋势判断** — 从这些变化中能看出的长期演进方向

## 差异数据
{diff_text}

## 当前版本上下文信息
{context_info}

请以 Markdown 格式输出报告。"""

    return await call_llm(prompt)

async def generate_scenario_analysis(scenario_key: str, scenario_name: str, extracted: dict) -> dict:
    """Generate LLM deep-dive analysis for a specific test scenario."""
    prompt = f"""你是一个 AI 系统分析专家。以下是 Claude Code 在「{scenario_name}」测试场景中的上下文工程数据。
请用中文分析：

1. **上下文组装策略** — 系统如何组织这个场景的上下文
2. **关键机制** — 这个场景触发了哪些特殊的上下文工程机制
3. **System Reminders** — 在工具结果中注入了哪些引导性内容，以及目的
4. **缓存策略** — 缓存配置及其对性能的影响

## 数据
- 模型: {extracted.get('model_used', '')}
- 系统提示词 blocks: {len(extracted.get('system_blocks', []))} 个
- 系统提示词总长: {len(extracted.get('system_prompt', ''))} chars
- 工具: {extracted.get('tool_names', [])}
- 延迟加载工具: {extracted.get('deferred_tools', [])}
- API 调用链: {json.dumps(extracted.get('api_calls', []), ensure_ascii=False)}
- 消息链: {json.dumps(extracted.get('messages_chain', []), ensure_ascii=False, indent=2)}
- System Reminders: {json.dumps(extracted.get('system_reminders', [])[:5], ensure_ascii=False)}
- 缓存策略: {json.dumps(extracted.get('cache_strategy', []), ensure_ascii=False)}

请以 Markdown 格式输出分析。"""

    return await call_llm(prompt)
```

**Step 2: Commit**

```bash
git add cc-observatory/backend/services/llm_analyzer.py
git commit -m "feat: add LLM analyzer service for report generation"
```

---

### Task 8: Scheduler and patrol orchestration

**Files:**
- Create: `cc-observatory/backend/services/scheduler.py`

**Step 1: Implement scheduler.py**

`cc-observatory/backend/services/scheduler.py`:
```python
import logging
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy.orm import Session

from backend.config import PATROL_INTERVAL_MINUTES, TRACES_DIR
from backend.database import SessionLocal
from backend.models import Version, TestRun, ExtractedData, VersionDiff, AnalysisReport, VersionStatus, RunStatus
from backend.services.version_checker import get_latest_npm_version, get_npm_metadata, install_claude_code_version
from backend.services.test_runner import run_single_prompt_scenario, run_multi_turn_scenario
from backend.services.extractor import extract_from_jsonl
from backend.services.differ import compute_version_diffs
from backend.services.llm_analyzer import generate_version_report, generate_scenario_analysis
from backend.scenarios import SCENARIOS

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()
_patrol_status = {"running": False, "last_run": None, "current_task": None, "error": None}

def get_patrol_status() -> dict:
    return {**_patrol_status}

async def run_patrol():
    """Main patrol job: detect new version, run scenarios, analyze, report."""
    if _patrol_status["running"]:
        logger.info("Patrol already running, skipping")
        return

    _patrol_status["running"] = True
    _patrol_status["current_task"] = "checking versions"
    _patrol_status["error"] = None

    db = SessionLocal()
    try:
        # 1. Check for new version
        latest = get_latest_npm_version()
        existing = db.query(Version).filter(Version.version == latest).first()
        if existing:
            logger.info(f"Version {latest} already processed")
            return

        logger.info(f"New version detected: {latest}")

        # 2. Create version record
        metadata = get_npm_metadata(latest)
        version = Version(version=latest, npm_metadata=metadata, status=VersionStatus.running)
        db.add(version)
        db.commit()

        # 3. Install claude-code
        _patrol_status["current_task"] = f"installing v{latest}"
        install_dir = str(TRACES_DIR / latest)
        cli_path = install_claude_code_version(latest, install_dir)

        # 4. Run all scenarios
        for scenario in SCENARIOS:
            _patrol_status["current_task"] = f"running {scenario['name']}"
            logger.info(f"Running scenario: {scenario['key']}")

            run = TestRun(
                version_id=version.id,
                scenario_key=scenario["key"],
                scenario_name=scenario["name"],
                scenario_group=scenario["group"],
                status=RunStatus.running,
                started_at=datetime.utcnow(),
            )
            db.add(run)
            db.commit()

            try:
                mode = scenario.get("mode", "single_prompt")
                if mode == "single_prompt":
                    trace_result = run_single_prompt_scenario(
                        cli_path, scenario["prompt"], scenario["key"], latest
                    )
                elif mode == "multi_turn":
                    trace_result = run_multi_turn_scenario(
                        cli_path, scenario["turns"], scenario["key"], latest
                    )
                elif mode == "paired":
                    # For paired scenarios (e.g., CLAUDE.md), run twice with different setups
                    # First run without CLAUDE.md
                    trace_result = run_single_prompt_scenario(
                        cli_path, scenario["prompt"], f"{scenario['key']}_without", latest
                    )
                    # TODO: second run with CLAUDE.md setup
                else:
                    trace_result = run_single_prompt_scenario(
                        cli_path, scenario["prompt"], scenario["key"], latest
                    )

                if trace_result["success"]:
                    run.raw_jsonl = trace_result["raw_jsonl"]
                    run.status = RunStatus.completed

                    # 5. Extract structured data
                    extracted = extract_from_jsonl(trace_result["raw_jsonl"])
                    ext_record = ExtractedData(
                        test_run_id=run.id,
                        system_prompt=extracted["system_prompt"],
                        system_blocks=extracted["system_blocks"],
                        tools=extracted["tools"],
                        tool_names=extracted["tool_names"],
                        deferred_tools=extracted["deferred_tools"],
                        messages_chain=extracted["messages_chain"],
                        api_calls=extracted["api_calls"],
                        system_reminders=extracted["system_reminders"],
                        cache_strategy=extracted["cache_strategy"],
                        token_usage=extracted["token_usage"],
                        model_used=extracted["model_used"],
                    )
                    db.add(ext_record)
                else:
                    run.status = RunStatus.failed
                    run.error_message = trace_result["error"]

            except Exception as e:
                run.status = RunStatus.failed
                run.error_message = str(e)
                logger.error(f"Scenario {scenario['key']} failed: {e}")

            run.finished_at = datetime.utcnow()
            db.commit()

        # 6. Compute diffs with previous version
        _patrol_status["current_task"] = "computing diffs"
        prev_version = (
            db.query(Version)
            .filter(Version.version != latest, Version.status == VersionStatus.completed)
            .order_by(Version.detected_at.desc())
            .first()
        )

        all_diffs = []
        if prev_version:
            for scenario in SCENARIOS:
                new_run = (
                    db.query(TestRun)
                    .filter(TestRun.version_id == version.id, TestRun.scenario_key == scenario["key"])
                    .first()
                )
                old_run = (
                    db.query(TestRun)
                    .filter(TestRun.version_id == prev_version.id, TestRun.scenario_key == scenario["key"])
                    .first()
                )
                if new_run and old_run and new_run.extracted and old_run.extracted:
                    new_ext = {
                        "system_prompt": new_run.extracted.system_prompt or "",
                        "tool_names": new_run.extracted.tool_names or [],
                        "system_reminders": new_run.extracted.system_reminders or [],
                    }
                    old_ext = {
                        "system_prompt": old_run.extracted.system_prompt or "",
                        "tool_names": old_run.extracted.tool_names or [],
                        "system_reminders": old_run.extracted.system_reminders or [],
                    }
                    diffs = compute_version_diffs(old_ext, new_ext)
                    for d in diffs:
                        diff_record = VersionDiff(
                            version_id=version.id,
                            prev_version_id=prev_version.id,
                            scenario_key=scenario["key"],
                            **d,
                        )
                        db.add(diff_record)
                        all_diffs.append(d)
            db.commit()

        # 7. Generate LLM reports
        _patrol_status["current_task"] = "generating LLM report"
        try:
            # Gather extracted samples for context
            extracted_samples = []
            for run in db.query(TestRun).filter(TestRun.version_id == version.id, TestRun.status == RunStatus.completed).all():
                if run.extracted:
                    extracted_samples.append({
                        "scenario_key": run.scenario_key,
                        "model_used": run.extracted.model_used,
                        "system_prompt": run.extracted.system_prompt or "",
                        "tool_names": run.extracted.tool_names or [],
                    })

            report_result = await generate_version_report(latest, all_diffs, extracted_samples)
            report = AnalysisReport(
                version_id=version.id,
                report_type="version_summary",
                title=f"Claude Code v{latest} 上下文工程分析报告",
                content=report_result["content"],
                model_used=report_result["model_used"],
                token_cost=report_result["token_cost"],
            )
            db.add(report)
        except Exception as e:
            logger.error(f"LLM report generation failed: {e}")

        version.status = VersionStatus.completed
        db.commit()
        logger.info(f"Patrol completed for v{latest}")

    except Exception as e:
        _patrol_status["error"] = str(e)
        logger.error(f"Patrol failed: {e}")
    finally:
        _patrol_status["running"] = False
        _patrol_status["last_run"] = datetime.utcnow().isoformat()
        _patrol_status["current_task"] = None
        db.close()

def start_scheduler():
    scheduler.add_job(run_patrol, "interval", minutes=PATROL_INTERVAL_MINUTES, id="patrol", replace_existing=True)
    scheduler.start()
    logger.info(f"Scheduler started, patrol every {PATROL_INTERVAL_MINUTES} minutes")
```

**Step 2: Update main.py to start scheduler on startup**

Add to lifespan in `cc-observatory/backend/main.py`:
```python
from backend.services.scheduler import start_scheduler

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    start_scheduler()
    yield
```

**Step 3: Commit**

```bash
git add cc-observatory/backend/services/scheduler.py cc-observatory/backend/main.py
git commit -m "feat: add scheduler service for auto-patrol orchestration"
```

---

## Phase 3: API Routes

### Task 9: Versions and test runs API routes

**Files:**
- Create: `cc-observatory/backend/routers/versions.py`
- Create: `cc-observatory/backend/routers/test_runs.py`
- Create: `cc-observatory/backend/routers/scenarios.py`
- Create: `cc-observatory/backend/routers/reports.py`
- Create: `cc-observatory/backend/routers/trends.py`
- Create: `cc-observatory/backend/routers/patrol.py`

**Step 1: Implement all routers**

`cc-observatory/backend/routers/versions.py`:
```python
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session, joinedload
from backend.database import get_db
from backend.models import Version, VersionDiff

router = APIRouter(prefix="/api/versions", tags=["versions"])

@router.get("")
def list_versions(skip: int = 0, limit: int = 50, db: Session = Depends(get_db)):
    versions = db.query(Version).order_by(Version.detected_at.desc()).offset(skip).limit(limit).all()
    return [
        {
            "id": v.id,
            "version": v.version,
            "detected_at": v.detected_at.isoformat() if v.detected_at else None,
            "status": v.status,
            "summary": v.summary,
            "test_run_count": len(v.test_runs),
            "report_count": len(v.reports),
        }
        for v in versions
    ]

@router.get("/latest")
def get_latest(db: Session = Depends(get_db)):
    v = db.query(Version).order_by(Version.detected_at.desc()).first()
    if not v:
        return None
    return {
        "id": v.id,
        "version": v.version,
        "detected_at": v.detected_at.isoformat() if v.detected_at else None,
        "status": v.status,
        "summary": v.summary,
    }

@router.get("/{version_id}")
def get_version(version_id: int, db: Session = Depends(get_db)):
    v = db.query(Version).options(joinedload(Version.test_runs), joinedload(Version.reports)).filter(Version.id == version_id).first()
    if not v:
        return {"error": "not found"}
    return {
        "id": v.id,
        "version": v.version,
        "detected_at": v.detected_at.isoformat() if v.detected_at else None,
        "npm_metadata": v.npm_metadata,
        "status": v.status,
        "summary": v.summary,
        "test_runs": [
            {
                "id": r.id,
                "scenario_key": r.scenario_key,
                "scenario_name": r.scenario_name,
                "scenario_group": r.scenario_group,
                "status": r.status,
                "started_at": r.started_at.isoformat() if r.started_at else None,
                "finished_at": r.finished_at.isoformat() if r.finished_at else None,
            }
            for r in v.test_runs
        ],
        "reports": [
            {
                "id": rp.id,
                "report_type": rp.report_type,
                "title": rp.title,
                "generated_at": rp.generated_at.isoformat() if rp.generated_at else None,
            }
            for rp in v.reports
        ],
    }

@router.get("/{version_id}/diff")
def get_version_diff(version_id: int, db: Session = Depends(get_db)):
    diffs = db.query(VersionDiff).filter(VersionDiff.version_id == version_id).all()
    return [
        {
            "id": d.id,
            "scenario_key": d.scenario_key,
            "diff_type": d.diff_type,
            "diff_content": d.diff_content,
            "change_summary": d.change_summary,
            "significance": d.significance,
        }
        for d in diffs
    ]
```

`cc-observatory/backend/routers/test_runs.py`:
```python
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session, joinedload
from backend.database import get_db
from backend.models import TestRun

router = APIRouter(prefix="/api/test-runs", tags=["test-runs"])

@router.get("")
def list_test_runs(
    version_id: int = None,
    scenario_key: str = None,
    db: Session = Depends(get_db),
):
    q = db.query(TestRun)
    if version_id:
        q = q.filter(TestRun.version_id == version_id)
    if scenario_key:
        q = q.filter(TestRun.scenario_key == scenario_key)
    runs = q.order_by(TestRun.started_at.desc()).all()
    return [
        {
            "id": r.id,
            "version_id": r.version_id,
            "scenario_key": r.scenario_key,
            "scenario_name": r.scenario_name,
            "scenario_group": r.scenario_group,
            "status": r.status,
            "started_at": r.started_at.isoformat() if r.started_at else None,
            "finished_at": r.finished_at.isoformat() if r.finished_at else None,
            "error_message": r.error_message,
        }
        for r in runs
    ]

@router.get("/{run_id}")
def get_test_run(run_id: int, db: Session = Depends(get_db)):
    r = db.query(TestRun).options(joinedload(TestRun.extracted)).filter(TestRun.id == run_id).first()
    if not r:
        return {"error": "not found"}
    result = {
        "id": r.id,
        "version_id": r.version_id,
        "scenario_key": r.scenario_key,
        "scenario_name": r.scenario_name,
        "scenario_group": r.scenario_group,
        "status": r.status,
        "started_at": r.started_at.isoformat() if r.started_at else None,
        "finished_at": r.finished_at.isoformat() if r.finished_at else None,
        "error_message": r.error_message,
    }
    if r.extracted:
        result["extracted"] = {
            "system_prompt": r.extracted.system_prompt,
            "system_blocks": r.extracted.system_blocks,
            "tools": r.extracted.tools,
            "tool_names": r.extracted.tool_names,
            "deferred_tools": r.extracted.deferred_tools,
            "messages_chain": r.extracted.messages_chain,
            "api_calls": r.extracted.api_calls,
            "system_reminders": r.extracted.system_reminders,
            "cache_strategy": r.extracted.cache_strategy,
            "token_usage": r.extracted.token_usage,
            "model_used": r.extracted.model_used,
        }
    return result

@router.get("/{run_id}/raw")
def get_raw_jsonl(run_id: int, db: Session = Depends(get_db)):
    r = db.query(TestRun).filter(TestRun.id == run_id).first()
    if not r:
        return {"error": "not found"}
    return {"raw_jsonl": r.raw_jsonl}
```

`cc-observatory/backend/routers/scenarios.py`:
```python
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models import TestRun, ExtractedData
from backend.scenarios import SCENARIOS

router = APIRouter(prefix="/api/scenarios", tags=["scenarios"])

@router.get("")
def list_scenarios():
    return SCENARIOS

@router.get("/{key}/history")
def scenario_history(key: str, db: Session = Depends(get_db)):
    runs = (
        db.query(TestRun)
        .filter(TestRun.scenario_key == key, TestRun.status == "completed")
        .order_by(TestRun.started_at.asc())
        .all()
    )
    history = []
    for r in runs:
        item = {
            "test_run_id": r.id,
            "version_id": r.version_id,
            "started_at": r.started_at.isoformat() if r.started_at else None,
        }
        if r.extracted:
            item["system_prompt_length"] = len(r.extracted.system_prompt or "")
            item["tool_count"] = len(r.extracted.tool_names or [])
            item["model_used"] = r.extracted.model_used
            item["token_usage"] = r.extracted.token_usage
        history.append(item)
    return history
```

`cc-observatory/backend/routers/reports.py`:
```python
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models import AnalysisReport

router = APIRouter(prefix="/api/reports", tags=["reports"])

@router.get("")
def list_reports(version_id: int = None, report_type: str = None, db: Session = Depends(get_db)):
    q = db.query(AnalysisReport)
    if version_id:
        q = q.filter(AnalysisReport.version_id == version_id)
    if report_type:
        q = q.filter(AnalysisReport.report_type == report_type)
    return [
        {
            "id": r.id,
            "version_id": r.version_id,
            "report_type": r.report_type,
            "title": r.title,
            "model_used": r.model_used,
            "generated_at": r.generated_at.isoformat() if r.generated_at else None,
            "token_cost": r.token_cost,
        }
        for r in q.order_by(AnalysisReport.generated_at.desc()).all()
    ]

@router.get("/{report_id}")
def get_report(report_id: int, db: Session = Depends(get_db)):
    r = db.query(AnalysisReport).filter(AnalysisReport.id == report_id).first()
    if not r:
        return {"error": "not found"}
    return {
        "id": r.id,
        "version_id": r.version_id,
        "report_type": r.report_type,
        "title": r.title,
        "content": r.content,
        "model_used": r.model_used,
        "generated_at": r.generated_at.isoformat() if r.generated_at else None,
        "token_cost": r.token_cost,
    }
```

`cc-observatory/backend/routers/trends.py`:
```python
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models import Version, TestRun

router = APIRouter(prefix="/api/trends", tags=["trends"])

@router.get("")
def get_trends(
    metric: str = Query("system_prompt_length", enum=["system_prompt_length", "tool_count", "token_usage"]),
    scenario_key: str = "basic_chat",
    db: Session = Depends(get_db),
):
    versions = db.query(Version).filter(Version.status == "completed").order_by(Version.detected_at.asc()).all()
    data_points = []
    for v in versions:
        run = (
            db.query(TestRun)
            .filter(TestRun.version_id == v.id, TestRun.scenario_key == scenario_key, TestRun.status == "completed")
            .first()
        )
        if not run or not run.extracted:
            continue
        value = None
        if metric == "system_prompt_length":
            value = len(run.extracted.system_prompt or "")
        elif metric == "tool_count":
            value = len(run.extracted.tool_names or [])
        elif metric == "token_usage":
            usage = run.extracted.token_usage or {}
            value = usage.get("input_tokens", 0) + usage.get("output_tokens", 0)

        data_points.append({
            "version": v.version,
            "detected_at": v.detected_at.isoformat() if v.detected_at else None,
            "value": value,
        })
    return {"metric": metric, "scenario_key": scenario_key, "data": data_points}
```

`cc-observatory/backend/routers/patrol.py`:
```python
from fastapi import APIRouter
from backend.services.scheduler import get_patrol_status, run_patrol
import asyncio

router = APIRouter(prefix="/api/patrol", tags=["patrol"])

@router.get("/status")
def patrol_status():
    return get_patrol_status()

@router.post("/trigger")
async def trigger_patrol():
    asyncio.create_task(run_patrol())
    return {"message": "Patrol triggered"}
```

**Step 2: Register all routers in main.py**

Update `cc-observatory/backend/main.py` to include all routers:
```python
from backend.routers import versions, test_runs, scenarios, reports, trends, patrol

app.include_router(versions.router)
app.include_router(test_runs.router)
app.include_router(scenarios.router)
app.include_router(reports.router)
app.include_router(trends.router)
app.include_router(patrol.router)
```

**Step 3: Verify API starts and responds**

Run: `cd cc-observatory && uvicorn backend.main:app --port 8000 --reload`
Test: `curl localhost:8000/api/scenarios | python -m json.tool`
Expected: Returns array of 14 scenarios

**Step 4: Commit**

```bash
git add cc-observatory/backend/routers/ cc-observatory/backend/main.py
git commit -m "feat: add all API routes (versions, test-runs, scenarios, reports, trends, patrol)"
```

---

## Phase 4: Frontend

### Task 10: Initialize React frontend project

**Step 1: Create Vite + React + TypeScript project**

```bash
cd cc-observatory
npm create vite@latest frontend -- --template react-ts
cd frontend
npm install
npm install -D tailwindcss @tailwindcss/vite
npm install react-router-dom recharts react-markdown @monaco-editor/react lucide-react clsx
```

**Step 2: Configure Tailwind**

Update `frontend/vite.config.ts`:
```typescript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    proxy: {
      '/api': 'http://localhost:8000',
    },
  },
})
```

Update `frontend/src/index.css`:
```css
@import "tailwindcss";
```

**Step 3: Create API client**

`frontend/src/lib/api.ts`:
```typescript
const BASE = '/api'

export async function fetchApi<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`)
  if (!res.ok) throw new Error(`API error: ${res.status}`)
  return res.json()
}

export async function postApi<T>(path: string, body?: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: body ? JSON.stringify(body) : undefined,
  })
  if (!res.ok) throw new Error(`API error: ${res.status}`)
  return res.json()
}
```

**Step 4: Create app router skeleton**

`frontend/src/App.tsx`:
```typescript
import { BrowserRouter, Routes, Route, Link } from 'react-router-dom'
import Dashboard from './pages/Dashboard'
import Timeline from './pages/Timeline'
import VersionDetail from './pages/VersionDetail'
import ScenarioDetail from './pages/ScenarioDetail'
import ScenarioHistory from './pages/ScenarioHistory'
import PatrolStatus from './pages/PatrolStatus'

export default function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-gray-950 text-gray-100">
        <nav className="border-b border-gray-800 px-6 py-3 flex items-center gap-6">
          <Link to="/" className="text-lg font-bold text-blue-400">CC Observatory</Link>
          <Link to="/timeline" className="text-sm text-gray-400 hover:text-gray-200">Timeline</Link>
          <Link to="/scenarios" className="text-sm text-gray-400 hover:text-gray-200">Scenarios</Link>
          <Link to="/patrol" className="text-sm text-gray-400 hover:text-gray-200">Patrol</Link>
        </nav>
        <main className="p-6">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/timeline" element={<Timeline />} />
            <Route path="/versions/:id" element={<VersionDetail />} />
            <Route path="/test-runs/:id" element={<ScenarioDetail />} />
            <Route path="/scenarios/:key" element={<ScenarioHistory />} />
            <Route path="/patrol" element={<PatrolStatus />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  )
}
```

**Step 5: Create placeholder pages (each will be implemented in subsequent tasks)**

Create placeholder files for each page in `frontend/src/pages/` — each exports a simple component with the page name.

**Step 6: Verify frontend starts**

Run: `cd cc-observatory/frontend && npm run dev`
Expected: Vite dev server at localhost:5173 shows "CC Observatory" nav

**Step 7: Commit**

```bash
git add cc-observatory/frontend/
git commit -m "feat: initialize React frontend with routing and Tailwind"
```

---

### Task 11: Dashboard page

**Files:**
- Create: `cc-observatory/frontend/src/pages/Dashboard.tsx`
- Create: `cc-observatory/frontend/src/components/VersionCard.tsx`
- Create: `cc-observatory/frontend/src/components/TrendChart.tsx`

Implement the Dashboard page with:
- 4 stat cards (tracked versions, latest version, last patrol time, changes found)
- Recent version changes list with significance badges (red/yellow/green)
- Trend chart (system prompt length over versions) using recharts LineChart

Fetch data from: `GET /api/versions`, `GET /api/versions/latest`, `GET /api/trends`, `GET /api/patrol/status`

**Commit:** `feat: implement Dashboard page with stats and trend chart`

---

### Task 12: Timeline page

**Files:**
- Create: `cc-observatory/frontend/src/pages/Timeline.tsx`

Implement vertical timeline view:
- Each node is a version, colored by significance (red=major, yellow=minor, green=none)
- Show version number, date, LLM summary snippet
- Click to navigate to `/versions/:id`
- Fetch from `GET /api/versions`

**Commit:** `feat: implement Timeline page with version nodes`

---

### Task 13: Version detail page

**Files:**
- Create: `cc-observatory/frontend/src/pages/VersionDetail.tsx`

Implement:
- Top section: LLM analysis report rendered as Markdown (react-markdown)
- Diff summary section with significance badges
- 14 scenario cards in a grid, grouped by category
- Each card shows: scenario name, status, key metrics (prompt length, tool count)
- Click card navigates to `/test-runs/:id`
- Fetch from: `GET /api/versions/:id`, `GET /api/versions/:id/diff`, `GET /api/reports?version_id=`

**Commit:** `feat: implement VersionDetail page with report and scenario cards`

---

### Task 14: Scenario detail page (core page)

**Files:**
- Create: `cc-observatory/frontend/src/pages/ScenarioDetail.tsx`
- Create: `cc-observatory/frontend/src/components/SystemPromptViewer.tsx`
- Create: `cc-observatory/frontend/src/components/MessageChainViz.tsx`
- Create: `cc-observatory/frontend/src/components/ToolsViewer.tsx`
- Create: `cc-observatory/frontend/src/components/ApiCallFlow.tsx`
- Create: `cc-observatory/frontend/src/components/DiffViewer.tsx`

Implement multi-tab layout:
- **Overview tab**: ApiCallFlow component showing sequence of API calls
- **System Prompt tab**: SystemPromptViewer with collapsible blocks, syntax highlighting
- **Message Chain tab**: MessageChainViz showing message roles, types, tool_use/tool_result flow
- **Tools tab**: ToolsViewer with tool names, descriptions, parameter schemas
- **Diff tab**: DiffViewer using @monaco-editor/react DiffEditor
- **Raw tab**: Raw JSONL viewer

Fetch from: `GET /api/test-runs/:id`, `GET /api/test-runs/:id/raw`, `GET /api/test-runs/:id/diff`

**Commit:** `feat: implement ScenarioDetail page with 6 analysis tabs`

---

### Task 15: Scenario history and patrol status pages

**Files:**
- Create: `cc-observatory/frontend/src/pages/ScenarioHistory.tsx`
- Create: `cc-observatory/frontend/src/pages/PatrolStatus.tsx`

**ScenarioHistory**: Line chart showing a scenario's metrics across all versions. Dropdown to select metric (prompt length, tool count, token usage). Table of all test runs for that scenario.

**PatrolStatus**: Current patrol status indicator, trigger button (POST /api/patrol/trigger), history log of past patrols.

**Commit:** `feat: implement ScenarioHistory and PatrolStatus pages`

---

## Phase 5: Containerization

### Task 16: Dockerfile and docker-compose

**Files:**
- Create: `cc-observatory/Dockerfile`
- Create: `cc-observatory/docker-compose.yml`
- Create: `cc-observatory/.dockerignore`

**Step 1: Create .dockerignore**

```
node_modules
frontend/node_modules
__pycache__
*.pyc
backend/data/
.git
```

**Step 2: Create Dockerfile (multi-stage)**

```dockerfile
# Stage 1: Build frontend
FROM node:20-slim AS frontend-build
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Stage 2: Python runtime with Node.js
FROM python:3.12-slim

RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y --no-install-recommends nodejs && \
    npm install -g @mariozechner/claude-trace && \
    apt-get purge -y curl && \
    apt-get autoremove -y && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ ./backend/
COPY --from=frontend-build /app/frontend/dist ./frontend/dist

RUN mkdir -p backend/data/traces

VOLUME /app/backend/data
EXPOSE 8000

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Step 3: Create docker-compose.yml**

```yaml
services:
  observatory:
    build: .
    ports:
      - "8000:8000"
    volumes:
      - observatory-data:/app/backend/data
    environment:
      - LLM_API_KEY=${LLM_API_KEY}
      - LLM_BASE_URL=${LLM_BASE_URL:-https://api.lkeap.cloud.tencent.com/coding/anthropic}
      - LLM_MODEL=${LLM_MODEL:-kimi-k2.5}
      - PATROL_INTERVAL_MINUTES=${PATROL_INTERVAL_MINUTES:-30}
      - CLAUDE_CODE_AUTH_TOKEN=${CLAUDE_CODE_AUTH_TOKEN}
    restart: unless-stopped

volumes:
  observatory-data:
```

**Step 4: Create .env file template**

`cc-observatory/.env.example`:
```
LLM_API_KEY=sk-sp-xxx
LLM_BASE_URL=https://api.lkeap.cloud.tencent.com/coding/anthropic
LLM_MODEL=kimi-k2.5
PATROL_INTERVAL_MINUTES=30
CLAUDE_CODE_AUTH_TOKEN=
```

**Step 5: Build and test**

Run: `cd cc-observatory && docker compose build && docker compose up -d`
Test: `curl localhost:8000/api/health`
Expected: `{"status":"ok"}`

**Step 6: Commit**

```bash
git add cc-observatory/Dockerfile cc-observatory/docker-compose.yml cc-observatory/.dockerignore cc-observatory/.env.example
git commit -m "feat: add Docker containerization with multi-stage build"
```

---

## Phase 6: Integration Testing & Polish

### Task 17: End-to-end integration test

**Step 1: Extract Claude Code OAuth token**

```bash
claude-trace --extract-token
```
Save the token to `.env` as `CLAUDE_CODE_AUTH_TOKEN`.

**Step 2: Trigger a manual patrol run**

```bash
curl -X POST localhost:8000/api/patrol/trigger
```

**Step 3: Monitor patrol status**

```bash
watch -n 5 'curl -s localhost:8000/api/patrol/status | python -m json.tool'
```

**Step 4: Verify data in API**

```bash
curl localhost:8000/api/versions | python -m json.tool
curl localhost:8000/api/test-runs?version_id=1 | python -m json.tool
curl localhost:8000/api/reports | python -m json.tool
```

**Step 5: Verify frontend renders data**

Open `http://localhost:8000` in browser, verify Dashboard shows stats and version data.

**Step 6: Commit**

```bash
git commit -m "test: verify end-to-end patrol and frontend rendering"
```

---

## Summary

| Phase | Tasks | Description |
|-------|-------|-------------|
| 1 | Tasks 1-2 | Project scaffolding, database models |
| 2 | Tasks 3-8 | Core services (version checker, test runner, extractor, differ, LLM analyzer, scheduler) |
| 3 | Task 9 | All API routes |
| 4 | Tasks 10-15 | Frontend pages and components |
| 5 | Task 16 | Docker containerization |
| 6 | Task 17 | Integration testing |

Total: **17 tasks**, estimated **6 phases**
