# Observatory 全量测试 Bug 修复计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 修复全量 Playwright 测试中发现的 6 个问题，确保所有页面和功能正常工作

**Architecture:** 前后端并行修复。后端修复数据格式和状态机问题，前端修复组件渲染和数据映射问题。每个 Task 独立可测试。

**Tech Stack:** Python/FastAPI (backend), React/TypeScript (frontend), SQLAlchemy, Recharts

---

### Task 1: 修复 Message Chain Tab 白屏崩溃

**根因：** 后端 extractor 返回的 `messages_chain` 格式是 `[{num_messages, summary}]`，但前端 `MessageChainViz` 组件期望 `[{turn, messages: [{role, content}]}]`。访问 `turn.messages.map()` 时 `messages` 为 undefined 导致 React 崩溃。

**方案：** 在 extractor 中保存完整的 messages 数据（截断超长内容），同时让前端组件兼容旧格式。

**Files:**
- Modify: `cc-observatory/backend/services/extractor.py:79-84`
- Modify: `cc-observatory/frontend/src/components/MessageChainViz.tsx:115-156`

**Step 1: 修改 extractor 保存完整 messages**

在 `cc-observatory/backend/services/extractor.py` 中，将第 79-84 行的 messages_chain 提取逻辑改为保存完整消息（截断内容以控制大小）：

```python
            # messages
            messages = body.get("messages", [])
            truncated_messages = _truncate_messages(messages)
            messages_chain.append({
                "num_messages": len(messages),
                "summary": _summarize_messages(messages),
                "messages": truncated_messages,
            })
```

在文件末尾添加 `_truncate_messages` 函数：

```python
def _truncate_messages(messages: list[dict], max_text_len: int = 1000) -> list[dict]:
    """Truncate message content to keep storage reasonable."""
    result = []
    for msg in messages:
        truncated = {"role": msg.get("role", "unknown")}
        content = msg.get("content", "")
        if isinstance(content, str):
            truncated["content"] = content[:max_text_len] + ("..." if len(content) > max_text_len else "")
        elif isinstance(content, list):
            truncated_blocks = []
            for block in content:
                if isinstance(block, dict):
                    b = dict(block)
                    if "text" in b and isinstance(b["text"], str) and len(b["text"]) > max_text_len:
                        b["text"] = b["text"][:max_text_len] + "..."
                    if "thinking" in b and isinstance(b["thinking"], str) and len(b["thinking"]) > max_text_len:
                        b["thinking"] = b["thinking"][:max_text_len] + "..."
                    truncated_blocks.append(b)
                else:
                    truncated_blocks.append(block)
            truncated["content"] = truncated_blocks
        else:
            truncated["content"] = str(content)[:max_text_len]
        result.append(truncated)
    return result
```

**Step 2: 修改 MessageChainViz 兼容两种格式**

在 `cc-observatory/frontend/src/components/MessageChainViz.tsx` 第 115 行 `export default function MessageChainViz` 中，添加对旧格式（无 messages 字段）的容错处理：

```tsx
export default function MessageChainViz({ chain }: MessageChainVizProps) {
  if (chain.length === 0) {
    return <p className="text-gray-400">No message chain data available.</p>
  }

  return (
    <div className="space-y-6">
      {chain.map((turn, ti) => {
        // 兼容旧格式：只有 num_messages + summary，没有 messages 数组
        if (!turn.messages || turn.messages.length === 0) {
          const summary = (turn as unknown as { summary?: string; num_messages?: number })
          return (
            <div key={ti} className="relative">
              <div className="text-xs text-gray-500 mb-2 font-medium">
                API Call Turn {turn.turn ?? ti + 1}
              </div>
              <div className="ml-4 border-l-2 border-gray-800 pl-4 py-2 text-sm text-gray-400">
                {summary.num_messages ?? 0} messages — {summary.summary ?? 'no details'}
              </div>
            </div>
          )
        }

        return (
          <div key={ti} className="relative">
            {/* 原有渲染逻辑不变 */}
```

**Step 3: 验证**

Run: 在浏览器打开 `http://localhost:8080/test-runs/55`，点击 Message Chain tab，确认不再白屏。
对于旧数据应显示摘要信息（如 "2 messages — 2 user"）。重新执行一次 patrol 后，新数据应显示完整消息链。

**Step 4: Commit**

```bash
git add cc-observatory/backend/services/extractor.py cc-observatory/frontend/src/components/MessageChainViz.tsx
git commit -m "fix: Message Chain tab crash - store full messages and handle legacy format"
```

---

### Task 2: 修复 ScenarioHistory 图表 X 轴显示 version_id 而非版本号

**根因：** 后端 `/api/scenarios/:key/history` 返回的 `version_id` 是 integer FK（如 1, 2, 3），前端直接用它做 X 轴标签。需要 JOIN Version 表获取实际版本号字符串。

**Files:**
- Modify: `cc-observatory/backend/routers/scenarios.py:18-44`
- Modify: `cc-observatory/frontend/src/pages/ScenarioHistory.tsx:71-74`

**Step 1: 后端 JOIN Version 表返回版本号**

修改 `cc-observatory/backend/routers/scenarios.py` 的 `scenario_history` 函数，JOIN Version 表获取版本号字符串：

```python
from backend.models import TestRun, Version  # 添加 Version import

@router.get("/{key}/history")
def scenario_history(key: str, db: Session = Depends(get_db)):
    runs = (
        db.query(TestRun)
        .options(joinedload(TestRun.extracted_data), joinedload(TestRun.version))
        .filter(TestRun.scenario_key == key, TestRun.status == "success")
        .order_by(TestRun.started_at.asc())
        .all()
    )
    result = []
    for run in runs:
        ed = run.extracted_data
        if not ed:
            continue
        system_prompt_length = len(ed.system_prompt) if ed.system_prompt else 0
        tool_names = _safe_json(ed.tool_names)
        tool_count = len(tool_names) if isinstance(tool_names, list) else 0
        result.append({
            "test_run_id": run.id,
            "version_id": run.version.version if run.version else str(run.version_id),
            "started_at": run.started_at.isoformat() if run.started_at else None,
            "system_prompt_length": system_prompt_length,
            "tool_count": tool_count,
            "model_used": ed.model_used,
            "token_usage": _safe_json(ed.token_usage),
        })
    return result
```

关键变更：`"version_id": run.version.version` — 通过 relationship 获取 Version.version 字符串（如 "2.1.73"）。

**Step 2: 验证**

Run: `curl -s "http://localhost:8080/api/scenarios/basic_chat/history" | python3 -m json.tool | head -20`
Expected: `"version_id"` 字段显示 "2.1.74", "2.1.70" 等字符串而非数字。

在浏览器打开 `http://localhost:8080/scenarios/basic_chat`，确认图表 X 轴和表格 Version 列显示版本号。

**Step 3: Commit**

```bash
git add cc-observatory/backend/routers/scenarios.py
git commit -m "fix: scenario history shows version string instead of numeric ID"
```

---

### Task 3: 修复卡在 "testing" 状态的版本 + 报告生成健壮性

**根因：**
- 版本卡在 testing：在 diff 计算阶段（第 245-302 行）发生未捕获异常时，`version_record.status = "analyzed"` 永远不会执行
- 报告为空：LLM API 调用失败（可能是 API key 配置或网络问题），异常被捕获但无报告生成

**方案：** (a) 确保状态必定推进（不管报告是否成功）；(b) 给 diff 计算加 try/except；(c) 添加修复存量数据的一次性 API

**Files:**
- Modify: `cc-observatory/backend/services/scheduler.py:143-320`
- Modify: `cc-observatory/backend/routers/patrol.py` (添加修复 endpoint)

**Step 1: 修改 scheduler 确保状态推进**

修改 `cc-observatory/backend/services/scheduler.py` 的 `_sync_patrol_for_version` 函数，将第 245-315 行的 diff 和 report 逻辑包裹在独立的 try/except 中：

```python
        # 5. Compute diffs (non-fatal)
        _patrol_status["current_task"] = f"computing diffs ({version})"
        try:
            prev_version = (
                db.query(Version)
                .filter(Version.id != version_record.id, Version.status.in_(["analyzed", "testing"]))
                .order_by(Version.detected_at.desc())
                .first()
            )
            # ... 原有 diff 逻辑 ...
            db.commit()
        except Exception:
            logger.exception("Error computing diffs for version %s", version)

        # 6. Generate LLM report (non-fatal)
        _patrol_status["current_task"] = f"generating LLM report ({version})"
        try:
            _sync_generate_report(db, version_record, version)
        except ImportError:
            logger.warning("llm_analyzer not available, skipping report generation.")
        except Exception:
            logger.exception("Error generating LLM report for version %s", version)

        # 7. ALWAYS mark version as analyzed (even if diff/report failed)
        version_record.status = "analyzed"
        db.commit()
        logger.info("Patrol completed for version %s", version)
```

**Step 2: 添加修复存量卡住版本的 API**

在 `cc-observatory/backend/routers/patrol.py` 中添加新 endpoint：

```python
@router.post("/fix-stuck")
async def fix_stuck_versions(db: Session = Depends(get_db)):
    """Fix versions stuck in 'testing' status by marking them as 'analyzed'."""
    stuck = db.query(Version).filter(Version.status == "testing").all()
    fixed = []
    for v in stuck:
        v.status = "analyzed"
        fixed.append(v.version)
    db.commit()
    return {"fixed": fixed, "count": len(fixed)}
```

**Step 3: 给 `_sync_generate_report` 添加日志**

在 `_sync_generate_report` 函数的 `if not extracted_samples: return` 处（第 357-358 行）添加日志：

```python
    if not extracted_samples:
        logger.warning("No extracted samples for version %s, skipping report.", version)
        return
```

**Step 4: 验证**

Run: `curl -X POST "http://localhost:8080/api/patrol/fix-stuck"`
Expected: `{"fixed": ["2.1.71", "2.1.70"], "count": 2}`

Run: `curl -s "http://localhost:8080/api/versions" | python3 -c "import sys,json; [print(v['version'],v['status']) for v in json.load(sys.stdin)]"`
Expected: 所有版本均为 "analyzed"

**Step 5: Commit**

```bash
git add cc-observatory/backend/services/scheduler.py cc-observatory/backend/routers/patrol.py
git commit -m "fix: prevent versions stuck in testing status, add fix-stuck endpoint"
```

---

### Task 4: 修复 token_usage 数据为空

**根因：** `claude-trace` 不捕获 `/v1/messages` 的响应 body（response.body 为 null），导致 extractor 无法从中提取 `usage` 字段。这是 claude-trace 工具本身的限制。

**方案：** 从 response headers 中尝试提取 token 信息（如果有），或者作为 fallback 在 Overview 中更友好地显示 "N/A"。同时，在 ScenarioDetail 的 Overview tab 中修正显示逻辑。

**Files:**
- Modify: `cc-observatory/backend/services/extractor.py:96-100`
- Modify: `cc-observatory/frontend/src/pages/ScenarioDetail.tsx:220-231`

**Step 1: 尝试从 response headers 或 streaming events 提取 token 信息**

在 `cc-observatory/backend/services/extractor.py` 中，修改 token_usage 提取逻辑，增加对 response headers 中 token 信息的读取尝试：

```python
            # token usage from response
            resp_body = _parse_body(response.get("body", {}))
            usage = resp_body.get("usage")
            if usage:
                token_usage = usage
            else:
                # Fallback: try to extract from response headers if available
                resp_headers = response.get("headers", {})
                input_tokens = resp_headers.get("x-ratelimit-input-tokens") or resp_headers.get("anthropic-ratelimit-input-tokens")
                output_tokens = resp_headers.get("x-ratelimit-output-tokens") or resp_headers.get("anthropic-ratelimit-output-tokens")
                if input_tokens or output_tokens:
                    token_usage = {
                        "input_tokens": int(input_tokens) if input_tokens else 0,
                        "output_tokens": int(output_tokens) if output_tokens else 0,
                        "source": "headers",
                    }
```

**Step 2: 修改前端 Token Usage 显示为 N/A 而非 0**

在 `cc-observatory/frontend/src/pages/ScenarioDetail.tsx` 第 220-231 行修改：

```tsx
        <MetricCard
          label="Token Usage"
          value={
            tokens && (tokens.input_tokens || tokens.output_tokens)
              ? `${((tokens.input_tokens ?? 0) + (tokens.output_tokens ?? 0)).toLocaleString()}`
              : 'N/A'
          }
          sub={
            tokens && (tokens.input_tokens || tokens.output_tokens)
              ? `In: ${(tokens.input_tokens ?? 0).toLocaleString()} / Out: ${(tokens.output_tokens ?? 0).toLocaleString()}`
              : 'claude-trace 未捕获响应体'
          }
        />
```

**Step 3: 验证**

在浏览器打开 `http://localhost:8080/test-runs/55` Overview tab，确认 Token Usage 显示 "N/A" 及解释文字。

**Step 4: Commit**

```bash
git add cc-observatory/backend/services/extractor.py cc-observatory/frontend/src/pages/ScenarioDetail.tsx
git commit -m "fix: handle missing token_usage gracefully with fallback and N/A display"
```

---

### Task 5: 修复 Diff Tab 功能不完整

**根因：** ScenarioDetail 的 Diff tab 传递的是 `ext.diff?.original` 和 `ext.diff?.modified`，但 ExtractedData 中没有 `diff` 字段。应该从同一场景的前一版本 test run 获取数据进行对比。

**方案：** 改为从后端获取同场景相邻版本的 system_prompt 进行 diff 对比。

**Files:**
- Modify: `cc-observatory/backend/routers/test_runs.py` (添加 diff 数据)
- Modify: `cc-observatory/frontend/src/pages/ScenarioDetail.tsx:171-176`

**Step 1: 后端在 test-run detail 中返回 diff 数据**

在 `cc-observatory/backend/routers/test_runs.py` 的 test run detail endpoint 中，查询同场景前一版本的 system_prompt 用于 diff：

在返回 test run detail 时，额外添加一个 `prev_system_prompt` 字段：

```python
# 在 get_test_run detail 函数中，查找同场景前一版本的数据
prev_run = (
    db.query(TestRun)
    .options(joinedload(TestRun.extracted_data))
    .filter(
        TestRun.scenario_key == run.scenario_key,
        TestRun.version_id < run.version_id,
        TestRun.status == "success",
    )
    .order_by(TestRun.version_id.desc())
    .first()
)

# 在响应中增加 diff 相关字段
result["diff_data"] = {
    "original": prev_run.extracted_data.system_prompt if prev_run and prev_run.extracted_data else None,
    "modified": run.extracted_data.system_prompt if run.extracted_data else None,
    "prev_version_id": prev_run.version_id if prev_run else None,
}
```

**Step 2: 前端 Diff tab 使用 diff_data**

修改 `cc-observatory/frontend/src/pages/ScenarioDetail.tsx` 第 171-176 行：

```tsx
        {activeTab === 'diff' && (
          <DiffViewer
            original={data.diff_data?.original}
            modified={data.diff_data?.modified}
            language="markdown"
          />
        )}
```

同时更新 `TestRunDetail` interface 添加 `diff_data` 字段：

```typescript
interface TestRunDetail {
  // ... 现有字段
  diff_data?: {
    original?: string
    modified?: string
    prev_version_id?: number
  }
}
```

**Step 3: 验证**

在浏览器打开 `http://localhost:8080/test-runs/55`，点击 Diff tab：
- 如果有前一版本数据，应显示 Monaco diff 对比视图
- 如果是第一个版本，仍显示 "Select two versions to compare"

**Step 4: Commit**

```bash
git add cc-observatory/backend/routers/test_runs.py cc-observatory/frontend/src/pages/ScenarioDetail.tsx
git commit -m "fix: Diff tab shows system prompt comparison with previous version"
```

---

### Task 6: 端到端 Playwright 回归测试

**Files:**
- 使用之前的测试脚本 `/tmp/test_all_pages.py` 和 `/tmp/test_deep_functional.py`

**Step 1: 修复存量数据**

```bash
curl -X POST "http://localhost:8080/api/patrol/fix-stuck"
```

**Step 2: 重建 Docker 镜像（包含全部后端修改）**

```bash
cd cc-observatory
docker compose up -d --build
```

**Step 3: 运行全量 Playwright 测试**

```bash
python3 /tmp/test_all_pages.py
python3 /tmp/test_deep_functional.py
```

Expected: 所有之前失败的测试项现在应通过。

**Step 4: 手动验证关键路径**

1. 打开 Dashboard → 点击版本 → 查看 VersionDetail
2. 点击 test run → ScenarioDetail → 依次切换 6 个 tab
3. 特别验证 Message Chain tab 不再白屏
4. 验证 Diff tab 显示 system prompt 差异
5. 打开 ScenarioHistory → 确认 X 轴显示版本号
6. 打开 PatrolStatus → 确认无 "testing" 状态版本

**Step 5: 最终 Commit**

```bash
git add -A
git commit -m "test: verify all 6 bugfixes with end-to-end testing"
```
