"""Draw a chat task's state as an RGB frame, for an env's ``render()``.

Every frame shows the model's latest reply and the task's latest message. When
the task answers in Wordle-style feedback (a row of letters over a row of
``G``/``Y``/``X``), the frame is a game view instead: the board, the latest
guess and feedback, and a keyboard of what each letter is known to be.
``terminal_frame`` draws a shell task (``terminal_env.py``): the task, the
model's latest reply, a strip of every tool call's outcome, and the shell
session with the tests' output once they ran.
"""

from __future__ import annotations

import functools
import json
import re
from typing import Any

import numpy as np
from PIL import Image, ImageDraw, ImageFont

WIDTH, HEIGHT = 1280, 720
MARGIN = 64
BG_TOP, BG_BOTTOM = (17, 21, 29), (10, 12, 17)
CARD, LINE = (22, 27, 36), (38, 44, 56)
INK, SOFT, MUTED = (236, 240, 246), (196, 204, 216), (128, 138, 154)
ACCENT = (110, 150, 255)
TILE = {"G": (63, 157, 99), "Y": (201, 162, 39), "X": (58, 63, 75)}
EMPTY_TILE, KEY = (20, 25, 32), (40, 46, 58)
STATUS = {
    "playing": ((30, 42, 66), (160, 188, 255)),
    "solved": ((24, 60, 40), (128, 224, 160)),
    "lost": ((66, 30, 34), (255, 150, 150)),
}
KEYBOARD = ("QWERTYUIOP", "ASDFGHJKL", "ZXCVBNM")
FEEDBACK = re.compile(r"^((?:[A-Z] )+[A-Z])\n((?:[GYX] )+[GYX])$", re.MULTILINE)
GUESS_TAG = re.compile(r"<guess>.*?</guess>", re.DOTALL)
ROWS = 6

FONTS = {
    "bold": ("Inter-Bold.otf", "DejaVuSans-Bold.ttf"),
    "semibold": ("Inter-SemiBold.otf", "DejaVuSans-Bold.ttf"),
    "regular": ("Inter-Regular.otf", "DejaVuSans.ttf"),
    "mono": ("JetBrainsMono-Bold.ttf", "DejaVuSansMono-Bold.ttf"),
    "terminal": ("JetBrainsMono-Regular.ttf", "DejaVuSansMono.ttf"),
}
TERMINAL_BG = (9, 11, 15)
GOOD, BAD, WARN = (128, 224, 160), (255, 150, 150), (232, 190, 90)
OUTCOME = {
    "ok": TILE["G"],
    "failed": (196, 72, 72),
    "timeout": TILE["Y"],
    "write": (86, 118, 214),
    "submit": (150, 110, 220),
    "pending": KEY,
}
ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]|\x1b\][^\x07]*\x07")


@functools.cache
def font(face: str, size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """``face`` at ``size`` from the system fonts, or Pillow's own font when none is installed."""
    for name in FONTS[face]:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default(size=size)


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


def frame(
    messages: list[dict[str, Any]], name: str, task_id: str, success: bool | None = None
) -> np.ndarray:
    """A ``HEIGHT x WIDTH x 3`` uint8 frame of the chat so far; ``success`` once the episode ended."""
    image, draw = _canvas()
    messages = [m for m in messages if m.get("role") != "system"]
    rows = board(messages)
    if rows or name.lower() == "wordle":
        rows = _with_final_guess(messages, rows, success)
        _game(draw, messages, rows, task_id)
    else:
        _header(draw, name.replace("_", " ").title(), f"task {task_id}", None)
        _chat(draw, messages)
    _footer(draw, messages)
    return np.asarray(image)


def tool_calls(messages: list[dict[str, Any]]) -> list[tuple[str, dict[str, Any], str | None]]:
    """Every ``(name, arguments, result)`` tool call in ``messages``; ``result`` is None until answered."""
    calls: list[list[Any]] = []
    open_calls: dict[Any, list[Any]] = {}
    for message in messages:
        if message.get("role") == "assistant":
            open_calls = {}
            for call in message.get("tool_calls") or []:
                function = call.get("function") or {}
                try:
                    args = json.loads(function.get("arguments") or "{}")
                except ValueError:
                    args = {}
                entry = [function.get("name") or "?", args if isinstance(args, dict) else {}, None]
                calls.append(entry)
                open_calls[call.get("id")] = entry
        elif message.get("role") == "tool" and message.get("tool_call_id") in open_calls:
            open_calls[message["tool_call_id"]][2] = text_of(message.get("content"))
    return [(name, args, result) for name, args, result in calls]


def outcome(name: str, result: str | None) -> str:
    """``ok``, ``failed``, ``timeout``, ``write``, ``submit`` or ``pending``."""
    if name == "submit":
        return "submit"
    if result is None:
        return "pending"
    if name == "write_file":
        return "write" if result.startswith("wrote ") else "failed"
    if result.startswith(("timed out", "skipped")):
        return "timeout"
    return "ok" if result.split("\n", 1)[0] == "exit code 0" else "failed"


def terminal_frame(
    messages: list[dict[str, Any]],
    name: str,
    instruction: str,
    cwd: str,
    turns: tuple[int, int],
    success: bool | None,
    verifier_log: str | None,
) -> np.ndarray:
    """A ``HEIGHT x WIDTH x 3`` uint8 frame of a shell task; ``success`` once the tests ran."""
    image, draw = _canvas()
    calls = tool_calls(messages)
    task = name.rsplit("/", 1)[-1]
    if success is None:
        status = ("playing", f"TURN {turns[0]} OF {turns[1]}")
    else:
        status = ("solved", "TESTS PASSED") if success else ("lost", "TESTS FAILED")
    _header(draw, "Terminal-Bench", task, status)

    left, right, top, bottom = MARGIN, MARGIN + 380, 128, HEIGHT - 64
    _panel(draw, (left, top, right, top + 196), "TASK")
    _lines(draw, instruction, (left + 24, top + 48), right - left - 48, 6, 16, 22)

    model_top = top + 212
    _panel(draw, (left, model_top, right, model_top + 168), "MODEL", accent=True)
    reply = next((m for m in reversed(messages) if m.get("role") == "assistant"), None)
    said = text_of(reply.get("content")).strip() if reply else ""
    asked = tool_calls([reply]) if reply else []
    if reply is None:
        said = "Reading the task"
    for name, args, _ in asked:
        detail = str(args.get("command") or args.get("path") or "").strip().split("\n")[0]
        said += ("\n" if said else "") + f"→ {name} {detail}".rstrip()
    _lines(draw, said or "(empty reply)", (left + 24, model_top + 48), right - left - 48, 5, 16, 22)

    strip_top = model_top + 184
    _panel(draw, (left, strip_top, right, bottom), "TOOL CALLS")
    kinds = [outcome(n, r) for n, _, r in calls]
    counts = (
        f"{sum(n == 'run_shell' for n, _, _ in calls)} commands  ·  "
        f"{kinds.count('failed')} failed  ·  {kinds.count('write')} files"
    )
    draw.text((left + 24, strip_top + 46), counts, font=font("regular", 15), fill=SOFT)
    size, gap = 14, 4
    per_row = int((right - left - 48 + gap) // (size + gap))
    rows = max(1, int((bottom - strip_top - 84 + gap) // (size + gap)))
    for i, kind in enumerate(kinds[-per_row * rows :]):
        x = left + 24 + (i % per_row) * (size + gap)
        y = strip_top + 76 + (i // per_row) * (size + gap)
        draw.rounded_rectangle((x, y, x + size, y + size), 3, OUTCOME[kind])

    box = (right + 24, top, WIDTH - MARGIN, bottom)
    _terminal(draw, box, f"root@{task}: {cwd}", _session(calls, verifier_log, success))
    _footer(draw, messages)
    return np.asarray(image)


def _session(calls, verifier_log: str | None, success: bool | None) -> list[tuple[str, tuple]]:
    """The shell session as ``(line, colour)``: older calls' output cut short, the latest in full."""
    lines: list[tuple[str, tuple]] = []

    def body(text: str, keep: int, colour=SOFT) -> None:
        rows = [_clean(row) for row in text.rstrip("\n").split("\n")] if text.strip() else []
        if len(rows) > keep:
            lines.append((f"  … {len(rows) - keep} more lines", MUTED))
            rows = rows[-keep:]
        lines.extend((row, colour) for row in rows)

    for i, (name, args, result) in enumerate(calls):
        keep = 40 if i == len(calls) - 1 else 6
        if name == "run_shell":
            command = str(args.get("command", "")).strip().split("\n")
            lines.append(("$ " + command[0], ACCENT))
            lines.extend(("> " + row, ACCENT) for row in command[1:3])
            if len(command) > 3:
                lines.append((f"> … {len(command) - 3} more lines", ACCENT))
            if result is None:
                continue
            head, _, rest = result.partition("\n")
            body(rest, keep)
            if outcome(name, result) == "timeout":
                lines.append((f"[{head}]", WARN))
            elif head != "exit code 0":
                lines.append((f"[{head}]", BAD))
        elif name == "write_file":
            content = str(args.get("content", ""))
            path = args.get("path", "?")
            lines.append((f"# write_file {path} ({len(content.splitlines())} lines)", OUTCOME["write"]))
            body(content, min(keep, 8), MUTED)
        elif name == "submit":
            lines.append(("$ bash /tests/test.sh", ACCENT))
        else:
            lines.append((f"# {name}: {result or ''}", BAD))
    if verifier_log is not None:
        if not any(name == "submit" for name, _, _ in calls):
            lines.append(("# out of turns; $ bash /tests/test.sh", WARN))
        body(verifier_log, 40)
    if success is not None:
        lines.append(("tests passed" if success else "tests failed", GOOD if success else BAD))
    return lines


def _clean(line: str) -> str:
    """One output line as a terminal shows it: no colour codes, tabs expanded, last ``\\r`` rewrite."""
    return ANSI.sub("", line).rsplit("\r", 1)[-1].expandtabs(4)


def _terminal(draw: ImageDraw.ImageDraw, box, title: str, lines) -> None:
    """A terminal window at ``box`` scrolled to the end of ``lines``."""
    x0, y0, x1, y1 = box
    draw.rounded_rectangle(box, 14, TERMINAL_BG, LINE, 1)
    for i, colour in enumerate(((196, 72, 72), TILE["Y"], TILE["G"])):
        draw.ellipse((x0 + 20 + i * 20, y0 + 15, x0 + 32 + i * 20, y0 + 27), colour)
    centre = ((x0 + x1) / 2, y0 + 21)
    draw.text(centre, title, font=font("terminal", 13), fill=MUTED, anchor="mm")
    draw.line((x0, y0 + 42, x1, y0 + 42), fill=LINE, width=1)
    face, height = font("terminal", 14), 19
    columns = max(20, int((x1 - x0 - 40) // draw.textlength("M", font=face)))
    rows = int((y1 - y0 - 64) // height)
    wrapped: list[tuple[str, tuple]] = []
    for text, colour in lines:
        pieces = [text[i : i + columns] for i in range(0, len(text), columns)] or [""]
        if len(pieces) > 3:
            pieces = pieces[:2] + [pieces[2][: columns - 1] + "…"]
        wrapped.extend((piece, colour) for piece in pieces)
    for i, (text, colour) in enumerate(wrapped[-rows:]):
        draw.text((x0 + 20, y0 + 56 + i * height), text, font=face, fill=colour)


def _canvas() -> tuple[Image.Image, ImageDraw.ImageDraw]:
    gradient = np.linspace(BG_TOP, BG_BOTTOM, HEIGHT).astype(np.uint8)
    image = Image.fromarray(np.repeat(gradient[:, None, :], WIDTH, axis=1))
    return image, ImageDraw.Draw(image)


def _footer(draw: ImageDraw.ImageDraw, messages) -> None:
    steps = sum(m.get("role") == "assistant" for m in messages)
    label = f"env.render()  ·  step {steps}"
    draw.text((MARGIN, HEIGHT - 36), label, font=font("regular", 14), fill=MUTED, anchor="lm")


def _with_final_guess(messages, rows, success: bool | None) -> list[tuple[str, str]]:
    """Add the episode's last guess, which a task may end on without a feedback row."""
    last = max((i for i, m in enumerate(messages) if m.get("role") == "assistant"), default=-1)
    later = messages[last + 1 :]
    if success is None or last < 0 or len(rows) >= ROWS:
        return rows
    if any(FEEDBACK.search(text_of(m.get("content"))) for m in later):
        return rows
    guess = re.findall(r"\[([A-Za-z]{5})\]", text_of(messages[last].get("content")))
    if not guess:
        return rows
    return [*rows, (guess[-1].upper(), "G" * 5 if success else "?" * 5)]


def _game(draw: ImageDraw.ImageDraw, messages, rows, task_id: str) -> None:
    if rows and set(rows[-1][1]) == {"G"}:
        status = ("solved", f"SOLVED IN {len(rows)}")
    elif len(rows) >= ROWS:
        status = ("lost", "OUT OF GUESSES")
    else:
        status = ("playing", f"GUESS {len(rows) + 1} OF {ROWS}")
    _header(draw, "Wordle", f"task {task_id}", status)

    tile, gap, top = 72, 10, 128
    bottom = top + ROWS * tile + (ROWS - 1) * gap
    for r in range(ROWS):
        word, marks = rows[r] if r < len(rows) else ("", "")
        y = top + r * (tile + gap)
        if r == len(rows) - 1:
            draw.rounded_rectangle((MARGIN - 20, y + 12, MARGIN - 14, y + tile - 12), 3, ACCENT)
        for c in range(5):
            x = MARGIN + c * (tile + gap)
            if c < len(marks):
                draw.rounded_rectangle((x, y, x + tile, y + tile), 8, TILE.get(marks[c], KEY))
            else:
                draw.rounded_rectangle((x, y, x + tile, y + tile), 8, EMPTY_TILE, LINE, 2)
            if c < len(word):
                centre = (x + tile / 2, y + tile / 2 + 1)
                draw.text(centre, word[c], font=font("bold", 36), fill=INK, anchor="mm")

    left, right = MARGIN + 5 * tile + 4 * gap + 64, WIDTH - MARGIN
    reply = next((m for m in reversed(messages) if m.get("role") == "assistant"), None)
    task = next((m for m in reversed(messages) if m.get("role") != "assistant"), None)

    _panel(draw, (left, top, right, top + 168), "MODEL")
    if reply is None:
        draw.text(
            (left + 24, top + 54),
            "Waiting for the first guess",
            font=font("regular", 19),
            fill=MUTED,
        )
    else:
        content = text_of(reply.get("content"))
        guess = re.findall(r"\[([A-Za-z]{5})\]", content)
        word = guess[-1].upper() if guess else "?????"
        draw.text((left + 24, top + 48), " ".join(word), font=font("mono", 40), fill=INK)
        reason = GUESS_TAG.sub("", content).strip() or "(no reasoning given)"
        _lines(draw, reason, (left + 24, top + 106), right - left - 48, 2)

    env_top = top + 184
    _panel(draw, (left, env_top, right, env_top + 108), "ENVIRONMENT")
    content = text_of(task.get("content")) if task else ""
    found = FEEDBACK.findall(content)
    note = FEEDBACK.sub("", content).strip()
    x = left + 24
    if found:
        letters, marks = (part.split() for part in found[-1])
        for letter, mark in zip(letters, marks):
            draw.rounded_rectangle((x, env_top + 48, x + 40, env_top + 88), 6, TILE[mark])
            centre = (x + 20, env_top + 69)
            draw.text(centre, letter, font=font("bold", 21), fill=INK, anchor="mm")
            x += 46
        x += 18
        _lines(draw, note, (x, env_top + 56), right - x - 24, 1)
    elif reply is not None and note:
        _lines(draw, note, (x, env_top + 46), right - x - 24, 2)
    else:
        rules = f"New game: find the five-letter word in {ROWS} guesses."
        _lines(draw, rules, (x, env_top + 56), right - x - 24, 1)

    known: dict[str, str] = {}
    for word, marks in rows:
        for letter, mark in zip(word, marks):
            if mark not in "GYX":
                continue
            if letter not in known or "GYX".index(mark) < "GYX".index(known[letter]):
                known[letter] = mark
    key_w, key_h, key_gap = 50, 48, 7
    for i, keys in enumerate(KEYBOARD):
        width = len(keys) * key_w + (len(keys) - 1) * key_gap
        x0 = (left + right - width) / 2
        y = bottom - (len(KEYBOARD) - i) * key_h - (len(KEYBOARD) - 1 - i) * key_gap
        for j, letter in enumerate(keys):
            x = x0 + j * (key_w + key_gap)
            mark = known.get(letter)
            draw.rounded_rectangle((x, y, x + key_w, y + key_h), 7, TILE[mark] if mark else KEY)
            centre = (x + key_w / 2, y + key_h / 2 + 1)
            ink = MUTED if mark == "X" else INK
            draw.text(centre, letter, font=font("semibold", 19), fill=ink, anchor="mm")


def _chat(draw: ImageDraw.ImageDraw, messages) -> None:
    """The latest messages, oldest at the top, as many as fit."""
    body, width = font("regular", 19), WIDTH - 2 * MARGIN - 160
    blocks = []
    room = HEIGHT - 64 - 128
    for message in reversed(messages):
        model = message.get("role") == "assistant"
        text = text_of(message.get("content")).strip()
        calls = [call["function"]["name"] for call in message.get("tool_calls") or []]
        if calls:
            text += ("\n" if text else "") + "Calls " + ", ".join(calls)
        lines = _wrap(draw, text or "(no text)", body, width - 48)
        lines = lines[:4] if len(lines) <= 4 else lines[:3] + [lines[3] + " …"]
        height = 54 + 27 * len(lines)
        if height > room:
            break
        blocks.append((model, lines, height))
        room -= height + 14
    y = 128
    for model, lines, height in reversed(blocks):
        left = MARGIN + (160 if model else 0)
        _panel(draw, (left, y, left + width, y + height), "MODEL" if model else "TASK", model)
        for i, line in enumerate(lines):
            draw.text((left + 24, y + 46 + 27 * i), line, font=body, fill=SOFT)
        y += height + 14


def _header(draw: ImageDraw.ImageDraw, title: str, subtitle: str, status) -> None:
    for i, colour in enumerate((TILE["G"], TILE["Y"], TILE["X"])):
        x = MARGIN + i * 16
        draw.rounded_rectangle((x, 52, x + 12, 64), 3, colour)
    draw.text((MARGIN + 60, 58), title, font=font("bold", 30), fill=INK, anchor="lm")
    title_w = draw.textlength(title, font=font("bold", 30))
    subtitle_at = (MARGIN + 76 + title_w, 60)
    draw.text(subtitle_at, subtitle, font=font("regular", 20), fill=MUTED, anchor="lm")
    if status is not None:
        kind, label = status
        fill, ink = STATUS[kind]
        width = draw.textlength(label, font=font("semibold", 15)) + 36
        box = (WIDTH - MARGIN - width, 40, WIDTH - MARGIN, 76)
        draw.rounded_rectangle(box, 18, fill)
        draw.text((box[0] + width / 2, 59), label, font=font("semibold", 15), fill=ink, anchor="mm")
    draw.line((MARGIN, 100, WIDTH - MARGIN, 100), fill=LINE, width=1)


def _panel(draw: ImageDraw.ImageDraw, box, label: str, accent: bool = False) -> None:
    draw.rounded_rectangle(box, 14, CARD, ACCENT if accent else LINE, 1)
    draw.text((box[0] + 24, box[1] + 20), label, font=font("semibold", 13), fill=MUTED)


def _lines(
    draw: ImageDraw.ImageDraw, text: str, at, width: float, limit: int, size=19, height=28
) -> None:
    body = font("regular", size)
    lines = _wrap(draw, text, body, width)
    if len(lines) > limit:
        lines = lines[: limit - 1] + [lines[limit - 1].rstrip(" .,") + " …"]
    for i, line in enumerate(lines):
        draw.text((at[0], at[1] + height * i), line, font=body, fill=SOFT)


def _wrap(draw: ImageDraw.ImageDraw, text: str, face, width: float) -> list[str]:
    lines: list[str] = []
    for paragraph in text.splitlines():
        line = ""
        for word in paragraph.split():
            candidate = f"{line} {word}".strip()
            if draw.textlength(candidate, font=face) <= width or not line:
                line = candidate
            else:
                lines.append(line)
                line = word
        if line:
            lines.append(line)
    return lines
