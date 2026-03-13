"""LLM analyzer service for generating version reports and scenario analyses."""

import httpx

from backend.config import ANTHROPIC_AUTH_TOKEN, ANTHROPIC_BASE_URL, LLM_MODEL


async def call_llm(prompt: str, model: str = None) -> dict:
    """Call the LLM API and return parsed response.

    Args:
        prompt: The user prompt to send.
        model: Model identifier override; defaults to LLM_MODEL from config.

    Returns:
        Dict with keys: content, model_used, token_cost.
    """
    model = model or LLM_MODEL
    url = f"{ANTHROPIC_BASE_URL}/v1/messages"
    headers = {
        "x-api-key": ANTHROPIC_AUTH_TOKEN,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    body = {
        "model": model,
        "max_tokens": 4096,
        "messages": [{"role": "user", "content": prompt}],
    }

    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(url, headers=headers, json=body)
        resp.raise_for_status()
        data = resp.json()

    # Extract text from content blocks
    text_parts = []
    for block in data.get("content", []):
        if block.get("type") == "text":
            text_parts.append(block["text"])
    content = "\n".join(text_parts)

    usage = data.get("usage", {})
    return {
        "content": content,
        "model_used": data.get("model", model),
        "token_cost": {
            "input": usage.get("input_tokens", 0),
            "output": usage.get("output_tokens", 0),
        },
    }


async def generate_version_report(
    version: str, diffs: list[dict], extracted_samples: list[dict]
) -> dict:
    """Generate an analytical report for a Claude Code version change.

    Args:
        version: The new version string.
        diffs: List of diff dicts, each with keys like file, content, etc.
        extracted_samples: Sample extracted scenario data for the new version.

    Returns:
        Dict from call_llm with the report in content.
    """
    # Format diffs section
    diffs_text = ""
    for i, d in enumerate(diffs, 1):
        file_name = d.get("file", d.get("name", f"diff_{i}"))
        diff_content = d.get("content", d.get("diff", ""))
        diffs_text += f"\n### Diff {i}: {file_name}\n```\n{diff_content}\n```\n"

    # Format extracted samples section
    samples_text = ""
    for i, s in enumerate(extracted_samples, 1):
        scenario = s.get("scenario_key", s.get("scenario", f"sample_{i}"))
        samples_text += f"\n### Sample {i}: {scenario}\n"
        for k, v in s.items():
            if k in ("scenario_key", "scenario"):
                continue
            samples_text += f"- **{k}**: {v}\n"

    prompt = f"""你是 Claude Code 版本变更分析专家。请根据以下信息对 Claude Code {version} 版本进行深入分析。

## 变更 Diff

{diffs_text}

## 提取的样本数据

{samples_text}

请从以下五个维度进行分析，使用 Markdown 格式输出：

### 1. 变更概述
简要总结本次版本更新的主要变更内容。

### 2. 上下文工程分析
分析 system prompt、工具定义、消息链等上下文工程层面的变化，包括 prompt 结构、指令措辞、工具能力等方面的调整。

### 3. 意图推测
基于变更内容，推测 Anthropic 团队的产品意图和技术方向。

### 4. 影响评估
评估这些变更对用户体验、模型行为、开发者工作流的潜在影响。

### 5. 趋势判断
结合已知的 Claude Code 发展脉络，判断这些变更所体现的产品演进趋势。
"""

    return await call_llm(prompt)


async def generate_scenario_analysis(
    scenario_key: str, scenario_name: str, extracted: dict
) -> dict:
    """Generate a deep analysis of a specific captured scenario.

    Args:
        scenario_key: Unique key for the scenario.
        scenario_name: Human-readable scenario name.
        extracted: Dict of extracted data including model, system_blocks,
                   prompt_length, tools, deferred_tools, api_calls,
                   messages_chain, system_reminders, cache_strategy, etc.

    Returns:
        Dict from call_llm with the analysis in content.
    """
    model = extracted.get("model", "unknown")
    system_blocks = extracted.get("system_blocks", 0)
    prompt_length = extracted.get("prompt_length", 0)
    tools = extracted.get("tools", [])
    deferred_tools = extracted.get("deferred_tools", [])
    api_calls = extracted.get("api_calls", [])
    messages_chain = extracted.get("messages_chain", [])
    system_reminders = extracted.get("system_reminders", [])
    cache_strategy = extracted.get("cache_strategy", "unknown")

    # Format list fields
    tools_text = "\n".join(f"  - {t}" for t in tools) if tools else "  (none)"
    deferred_text = (
        "\n".join(f"  - {t}" for t in deferred_tools) if deferred_tools else "  (none)"
    )
    api_calls_text = (
        "\n".join(f"  - {a}" for a in api_calls) if api_calls else "  (none)"
    )
    messages_text = ""
    for m in messages_chain:
        role = m.get("role", "unknown") if isinstance(m, dict) else str(m)
        messages_text += f"  - {role}\n"
    if not messages_text:
        messages_text = "  (none)\n"

    reminders_text = (
        "\n".join(f"  - {r}" for r in system_reminders)
        if system_reminders
        else "  (none)"
    )

    prompt = f"""你是 Claude Code 上下文工程分析专家。请对以下场景进行深度分析。

## 场景信息

- **场景 Key**: {scenario_key}
- **场景名称**: {scenario_name}
- **使用模型**: {model}
- **System Blocks 数量**: {system_blocks}
- **Prompt 总长度**: {prompt_length}
- **缓存策略**: {cache_strategy}

## 工具列表
{tools_text}

## 延迟加载工具
{deferred_text}

## API 调用
{api_calls_text}

## 消息链
{messages_text}
## System Reminders
{reminders_text}

请从以下角度进行深入分析，使用 Markdown 格式输出：

### 1. 场景概述
概括该场景的用途和触发条件。

### 2. 上下文工程策略
分析 system prompt 的结构设计、缓存策略选择、工具配置逻辑、延迟加载策略等。

### 3. Prompt 设计分析
分析 prompt 的措辞风格、指令层次、约束条件设置等。

### 4. 工具链分析
分析工具的选择、组合方式、延迟加载工具的设计意图。

### 5. 优化建议
基于分析，给出可能的优化方向或值得关注的设计模式。
"""

    return await call_llm(prompt)
