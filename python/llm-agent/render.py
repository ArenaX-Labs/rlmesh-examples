"""Draw a chat task's state as an RGB frame, for an env's ``render()``.

The frame shows the latest assistant reply and the task's latest message. When
the task's messages hold Wordle-style feedback (a row of letters over a row of
``G``/``Y``/``X``), a board of every guess so far is drawn beside them.
"""

from __future__ import annotations

import re
import textwrap
from typing import Any

import numpy as np
from PIL import Image, ImageDraw, ImageFont

WIDTH, HEIGHT = 960, 540
BG, FG, DIM, PANEL, EMPTY = (
    (18, 21, 27),
    (226, 230, 237),
    (140, 148, 162),
    (30, 35, 45),
    (34, 38, 47),
)
TILE = {"G": (83, 141, 78), "Y": (181, 159, 59), "X": (61, 64, 72)}
FEEDBACK = re.compile(r"^((?:[A-Z] )+[A-Z])\n((?:[GYX] )+[GYX])$", re.MULTILINE)


def text_of(content: Any) -> str:
    """The text of an OpenAI message ``content`` (a string or a list of parts)."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(part.get("text", "") for part in content if isinstance(part, dict))
    return ""


def board(messages: list[dict[str, Any]]) -> list[tuple[str, str]]:
    """Every ``(letters, marks)`` feedback row in ``messages``, in order."""
    rows = []
    for message in messages:
        if message.get("role") != "assistant":
            for letters, marks in FEEDBACK.findall(text_of(message.get("content"))):
                rows.append((letters.replace(" ", ""), marks.replace(" ", "")))
    return rows


def frame(messages: list[dict[str, Any]], title: str) -> np.ndarray:
    """An ``HEIGHT x WIDTH x 3`` uint8 frame of the chat so far."""
    image = Image.new("RGB", (WIDTH, HEIGHT), BG)
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default(size=18)
    draw.text((24, 18), title, font=ImageFont.load_default(size=22), fill=FG)

    left = 24
    rows = board(messages)
    if rows:
        tile, gap, letters = 52, 6, ImageFont.load_default(size=30)
        width = max(len(word) for word, _ in rows)
        for r in range(max(6, len(rows))):
            for c in range(width):
                x, y = 24 + c * (tile + gap), 64 + r * (tile + gap)
                word, marks = rows[r] if r < len(rows) else ("", "")
                fill = TILE.get(marks[c : c + 1], EMPTY)
                draw.rectangle((x, y, x + tile, y + tile), fill=fill)
                if c < len(word):
                    draw.text(
                        (x + tile / 2, y + tile / 2), word[c], font=letters, fill=FG, anchor="mm"
                    )
        left = 24 + width * (tile + gap) + 18

    reply = next((m for m in reversed(messages) if m.get("role") == "assistant"), None)
    task = next((m for m in reversed(messages) if m.get("role") != "assistant"), None)
    y = 64
    for label, message in (("Model", reply), ("Task", task)):
        if message is None:
            continue
        text = text_of(message.get("content")).strip() or "(no text)"
        calls = [call["function"]["name"] for call in message.get("tool_calls") or []]
        if calls:
            text += "\n[tools: " + ", ".join(calls) + "]"
        lines = [line for para in text.splitlines() for line in textwrap.wrap(para, 68) or [""]]
        lines = lines[-9:]
        height = 40 + 24 * len(lines)
        draw.rounded_rectangle((left, y, WIDTH - 24, y + height), radius=8, fill=PANEL)
        draw.text((left + 14, y + 10), label, font=font, fill=DIM)
        for i, line in enumerate(lines):
            draw.text((left + 14, y + 34 + 24 * i), line, font=font, fill=FG)
        y += height + 14
    return np.asarray(image)
