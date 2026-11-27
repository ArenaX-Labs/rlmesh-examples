"""Write an agent episode as an ATIF trajectory, the format Harbor's tools read.

One JSON document per episode, rewritten after every step so the file on disk
is always a complete trajectory:
https://github.com/harbor-framework/harbor/blob/main/rfcs/0001-trajectory-format.md
"""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

Message = dict[str, Any]
SCHEMA_VERSION = "ATIF-v1.8"


class Trajectory:
    """One episode's steps: what the env said, and each agent turn with its tool results."""

    def __init__(
        self, path: Path, episode_id: str, seed: int | None, agent: str, model: str
    ) -> None:
        self.path = path
        self.steps: list[dict[str, Any]] = []
        self.document: dict[str, Any] = {
            "schema_version": SCHEMA_VERSION,
            "session_id": episode_id,
            "agent": {"name": agent, "version": "1", "model_name": model},
            "steps": self.steps,
            "extra": {"seed": seed},
        }

    def observe(self, messages: list[Message], tools: list[dict[str, Any]]) -> None:
        """Add the env's new messages; a tool result joins the agent step that made the call."""
        if tools:
            self.document["agent"]["tool_definitions"] = tools
        for message in messages:
            role = message.get("role")
            if role == "tool" and self.steps and self.steps[-1]["source"] == "agent":
                results = self.steps[-1].setdefault("observation", {"results": []})["results"]
                results.append(
                    {
                        "source_call_id": message.get("tool_call_id"),
                        "content": _text(message.get("content")),
                    }
                )
            else:
                source = "system" if role == "system" else "user"
                self._step(source, _text(message.get("content")))

    def reply(
        self,
        message: Message,
        usages: list[dict[str, Any]],
        *,
        rlmesh_step: int,
        latency_ms: float,
        error: str | None = None,
    ) -> None:
        """Add one agent turn: the reply the env receives, over however many LLM calls it took."""
        step = self._step("agent", _text(message.get("content")))
        step["model_name"] = self.document["agent"]["model_name"]
        if reasoning := message.get("reasoning"):
            step["reasoning_content"] = reasoning
        if calls := message.get("tool_calls"):
            step["tool_calls"] = [_tool_call(call) for call in calls]
        if metrics := _metrics(usages):
            step["metrics"] = metrics
        step["llm_call_count"] = max(len(usages), 1)
        extra: dict[str, Any] = {"rlmesh_step": rlmesh_step, "latency_ms": latency_ms}
        stop = next((u["stop_reason"] for u in reversed(usages) if u.get("stop_reason")), None)
        if stop:
            extra["stop_reason"] = stop
        if error:
            extra["error"] = error
        step["extra"] = extra

    def save(self) -> None:
        agent_steps = [step for step in self.steps if step["source"] == "agent"]
        totals = [step.get("metrics", {}) for step in agent_steps]
        self.document["final_metrics"] = {
            "total_prompt_tokens": sum(m.get("prompt_tokens", 0) for m in totals),
            "total_completion_tokens": sum(m.get("completion_tokens", 0) for m in totals),
            "total_cached_tokens": sum(m.get("cached_tokens", 0) for m in totals),
            "total_steps": len(self.steps),
        }
        scratch = self.path.with_suffix(".tmp")
        scratch.write_text(json.dumps(self.document, default=str))
        os.replace(scratch, self.path)

    def _step(self, source: str, message: str) -> dict[str, Any]:
        step = {
            "step_id": len(self.steps) + 1,
            "timestamp": datetime.now(UTC).isoformat(timespec="milliseconds"),
            "source": source,
            "message": message,
        }
        self.steps.append(step)
        return step


def _text(content: Any) -> str:
    """Flatten chat content to text; an image becomes its MIME type and size, never its bytes."""
    if not isinstance(content, list):
        return content or ""
    parts: list[str] = []
    for part in content:
        url = (part.get("image_url") or {}).get("url", "") if isinstance(part, dict) else ""
        if url.startswith("data:"):
            header, _, payload = url.partition(",")
            parts.append(
                f"[image {header.removeprefix('data:').split(';')[0]}, {len(payload)} bytes]"
            )
        elif url:
            parts.append(f"[image {url}]")
        elif isinstance(part, dict) and part.get("text"):
            parts.append(part["text"])
    return "\n".join(parts)


def _tool_call(call: dict[str, Any]) -> dict[str, Any]:
    function = call.get("function", {})
    try:
        arguments = json.loads(function.get("arguments") or "{}")
    except ValueError:
        arguments = {"_raw": function.get("arguments")}
    return {
        "tool_call_id": call.get("id", ""),
        "function_name": function.get("name", ""),
        "arguments": arguments if isinstance(arguments, dict) else {"_raw": arguments},
    }


def _metrics(usages: list[dict[str, Any]]) -> dict[str, int]:
    """Sum OpenAI- or Anthropic-shaped usage; Anthropic reports cached input apart from input."""
    prompt = completion = cached = 0
    for usage in usages:
        read = usage.get("cache_read_input_tokens") or (
            usage.get("prompt_tokens_details") or {}
        ).get("cached_tokens", 0)
        cached += read or 0
        if "input_tokens" in usage:
            prompt += (
                usage["input_tokens"]
                + (read or 0)
                + (usage.get("cache_creation_input_tokens") or 0)
            )
        else:
            prompt += usage.get("prompt_tokens") or 0
        completion += usage.get("output_tokens") or usage.get("completion_tokens") or 0
    if not usages:
        return {}
    return {"prompt_tokens": prompt, "completion_tokens": completion, "cached_tokens": cached}
