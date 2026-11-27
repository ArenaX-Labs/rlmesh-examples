"""An LLM agent as an RLMesh model: one predict is one env interaction.

Each episode is written as an ATIF trajectory (``trajectory.py``) to
``$RLMESH_OUTPUT_DIR/trajectories/<episode_id>.json``.
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
from collections.abc import Callable
from typing import Any

import rlmesh
from chat_env import Message, output_dir
from rlmesh.types import PredictContext
from trajectory import Trajectory

Chat = Callable[[list[Message], list[dict[str, Any]]], tuple[Message, dict[str, Any] | None]]
DEFAULT_MODEL = "qwen3:4b"
DEFAULT_BASE_URL = "http://localhost:11434/v1"
DEFAULT_MAX_TOKENS = 8192
# RLMesh abandons a predict after 300 s; one call and the retries stop before that.
STEP_BUDGET_S = 240.0


def openai_chat(model: str, max_tokens: int = DEFAULT_MAX_TOKENS) -> Chat:
    """Chat through the OpenAI-compatible server at ``$OPENAI_BASE_URL``."""
    from openai import OpenAI, omit

    # Messages and tools pass through as plain JSON, not the SDK's TypedDicts.
    client: Any = OpenAI(
        base_url=os.environ.get("OPENAI_BASE_URL", DEFAULT_BASE_URL),
        api_key=os.environ.get("OPENAI_API_KEY", "ollama"),
        timeout=STEP_BUDGET_S,
        max_retries=0,
    )

    def chat(
        messages: list[Message], tools: list[dict[str, Any]]
    ) -> tuple[Message, dict[str, Any] | None]:
        completion = client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=max_tokens,
            # Ollama's thinking switch: reasoning moves out of content; other servers ignore it.
            extra_body={"think": False},
            tools=tools or omit,
        )
        message = completion.choices[0].message.model_dump(exclude_none=True)
        reply: Message = {"role": "assistant", "content": message.get("content")}
        for key in ("tool_calls", "reasoning"):
            if message.get(key):
                reply[key] = message[key]
        usage = completion.usage.model_dump() if completion.usage else None
        return reply, usage

    return chat


def anthropic_chat(model: str, max_tokens: int = DEFAULT_MAX_TOKENS) -> Chat:
    """Chat through Anthropic's Messages API (``$ANTHROPIC_API_KEY``), keeping Claude's thinking.

    The reply's ``reasoning`` is Claude's summarized thinking; ``anthropic_content`` holds the
    raw content blocks, which the next call must send back unchanged.
    """
    import anthropic

    client: Any = anthropic.Anthropic(timeout=STEP_BUDGET_S, max_retries=0)

    def chat(
        messages: list[Message], tools: list[dict[str, Any]]
    ) -> tuple[Message, dict[str, Any] | None]:
        system, turns = _anthropic_messages(messages)
        extra: dict[str, Any] = {}
        if system:
            extra["system"] = system
        if tools:
            extra["tools"] = [_anthropic_tool(tool) for tool in tools]
        # No refusal fallback: a different model answering would change what is evaluated.
        response = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            thinking={"type": "adaptive", "display": "summarized"},
            messages=turns,
            **extra,
        )
        blocks = response.content
        text = "".join(block.text for block in blocks if block.type == "text")
        reply: Message = {"role": "assistant", "content": text}
        calls = [
            {
                "id": block.id,
                "type": "function",
                "function": {"name": block.name, "arguments": json.dumps(block.input)},
            }
            for block in blocks
            if block.type == "tool_use"
        ]
        if calls:
            reply["tool_calls"] = calls
        thinking = "\n\n".join(b.thinking for b in blocks if b.type == "thinking" and b.thinking)
        if thinking:
            reply["reasoning"] = thinking
        reply["anthropic_content"] = [block.model_dump(exclude_none=True) for block in blocks]
        usage = response.usage.model_dump(exclude_none=True)
        usage["stop_reason"] = response.stop_reason
        return reply, usage

    return chat


def _anthropic_messages(messages: list[Message]) -> tuple[str, list[dict[str, Any]]]:
    """Split OpenAI-style chat into Anthropic's system prompt and turns."""
    system: list[str] = []
    turns: list[dict[str, Any]] = []
    for message in messages:
        role, content = message["role"], message.get("content")
        if role == "system" and not turns:
            system.append(_text(content))
        elif role == "assistant":
            blocks = message.get("anthropic_content") or _assistant_blocks(message)
            if blocks:
                turns.append({"role": "assistant", "content": blocks})
        elif role == "tool":
            result = {
                "type": "tool_result",
                "tool_use_id": message["tool_call_id"],
                "content": _text(content),
            }
            last = turns[-1] if turns else None
            if last and last["role"] == "user" and last["content"][-1]["type"] == "tool_result":
                last["content"].append(result)
            else:
                turns.append({"role": "user", "content": [result]})
        else:
            turns.append({"role": "user", "content": _user_blocks(content)})
    return "\n\n".join(system), turns


def _text(content: Any) -> str:
    if isinstance(content, list):
        return "".join(part.get("text", "") for part in content if isinstance(part, dict))
    return content or ""


def _user_blocks(content: Any) -> list[dict[str, Any]]:
    if not isinstance(content, list):
        return [{"type": "text", "text": content or "(empty)"}]
    blocks = []
    for part in content:
        if part.get("type") == "image_url":
            url = part["image_url"]["url"]
            if url.startswith("data:"):
                header, _, data = url.partition(",")
                media_type = header.removeprefix("data:").split(";")[0]
                source = {"type": "base64", "media_type": media_type, "data": data}
            else:
                source = {"type": "url", "url": url}
            blocks.append({"type": "image", "source": source})
        elif part.get("text"):
            blocks.append({"type": "text", "text": part["text"]})
    return blocks or [{"type": "text", "text": "(empty)"}]


def _assistant_blocks(message: Message) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = []
    if text := _text(message.get("content")):
        blocks.append({"type": "text", "text": text})
    for call in message.get("tool_calls") or []:
        function = call["function"]
        blocks.append(
            {
                "type": "tool_use",
                "id": call["id"],
                "name": function["name"],
                "input": json.loads(function.get("arguments") or "{}"),
            }
        )
    return blocks


def _anthropic_tool(tool: dict[str, Any]) -> dict[str, Any]:
    function = tool["function"]
    return {
        "name": function["name"],
        "description": function.get("description", ""),
        "input_schema": function.get("parameters") or {"type": "object", "properties": {}},
    }


_DATA_URL = re.compile(r"(data:[\w/+.-]+;base64,)[A-Za-z0-9+/=]+")


def _log_step(episode: str, step: int, reply: Message, usage: dict[str, Any] | None) -> None:
    """Print one line per step, so a run's log shows what the agent did."""
    said = " ".join(str(reply.get("content") or "").split())
    calls = [call["function"]["name"] for call in reply.get("tool_calls") or []]
    thought = " ".join(str(reply.get("reasoning") or "").split())
    parts = [f"[{episode[-8:]} step {step}]", repr(said[-120:])]
    if calls:
        parts.append(f"tools={calls}")
    if usage:
        parts.append(f"tokens={usage.get('output_tokens') or usage.get('completion_tokens')}")
    if thought:
        parts.append(f"thinking={thought[:200]!r}")
    print(" ".join(parts), file=sys.stderr, flush=True)


class LLMHarness(rlmesh.Model):
    """Answer each observation with the LLM's next assistant message.

    Args:
        model: The model name sent to the chat server (default ``$OPENAI_MODEL``).
        chat: The chat function; defaults to :func:`anthropic_chat` when ``$ANTHROPIC_API_KEY``
            is set, else :func:`openai_chat`.
        retries: Extra calls allowed in one step when a reply is empty.
        max_tokens: The completion budget of each call, reasoning included
            (default ``$OPENAI_MAX_TOKENS``).
    """

    def __init__(
        self,
        model: str | None = None,
        chat: Chat | None = None,
        retries: int = 2,
        max_tokens: int | None = None,
    ) -> None:
        model = model or os.environ.get("OPENAI_MODEL", DEFAULT_MODEL)
        max_tokens = max_tokens or int(os.environ.get("OPENAI_MAX_TOKENS") or DEFAULT_MAX_TOKENS)
        self.model_name = model
        backend = anthropic_chat if os.environ.get("ANTHROPIC_API_KEY") else openai_chat
        self.chat = chat or backend(model, max_tokens)
        self.system_prompt = os.environ.get("OPENAI_SYSTEM_PROMPT", "")
        self.retries = retries
        self.trajectories = output_dir() / "trajectories"
        self.trajectories.mkdir(exist_ok=True)
        super().__init__()

    def predict(self, observation: str, context: PredictContext) -> str:
        try:
            obs = json.loads(observation)
        except ValueError:
            obs = None
        if not isinstance(obs, dict):
            # A probe samples random text; answer it without the LLM.
            return json.dumps({"role": "assistant", "content": ""})
        tools: list[dict[str, Any]] = obs["tools"]
        state = context["state"]
        messages: list[Message] = state.setdefault("messages", [])
        episode = context["episode_id"] or "episode"
        trajectory: Trajectory = state.get("trajectory") or state.setdefault(
            "trajectory",
            Trajectory(
                self.trajectories / f"{episode}.json",
                episode,
                context["episode_seed"],
                "llm-harness",
                self.model_name,
            ),
        )
        new: list[Message] = obs["messages"]
        if not messages and self.system_prompt:
            new = [{"role": "system", "content": self.system_prompt}, *new]
        messages.extend(new)
        trajectory.observe(new, tools)
        reply: Message = {"role": "assistant", "content": ""}
        usages: list[dict[str, Any]] = []
        error: str | None = None
        step_started = time.monotonic()
        try:
            for _ in range(1 + self.retries):
                started = time.monotonic()
                reply, usage = self.chat(messages, tools)
                if usage:
                    usages.append(usage)
                if reply.get("content") or reply.get("tool_calls"):
                    break
                now = time.monotonic()
                if now - step_started + (now - started) > STEP_BUDGET_S:
                    break
        except Exception as exc:
            error = _DATA_URL.sub(r"\1<redacted>", repr(exc))
            raise
        finally:
            trajectory.reply(
                reply,
                usages,
                rlmesh_step=context["predict_index"],
                latency_ms=round((time.monotonic() - step_started) * 1000, 1),
                error=error,
            )
            trajectory.save()
        _log_step(episode, context["predict_index"], reply, usages[-1] if usages else None)
        reply.pop("reasoning", None)
        native = reply.pop("anthropic_content", None)
        messages.append({**reply, "anthropic_content": native} if native else reply)
        return json.dumps(reply)
