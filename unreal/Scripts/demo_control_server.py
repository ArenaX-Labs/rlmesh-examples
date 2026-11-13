"""Optional in-editor HTTP API to swap and play RLMesh environments.

Sample helper for this project only — not part of the RLMesh plugin.
Starts automatically in the editor via PostPIEStarted / ARLMeshDemoGameMode
(PythonScriptPlugin). Manual start in the Output Log::

  py "Scripts/demo_control_server.py"

CLI (from this project root)::

  python Scripts/demo_client.py list
  python Scripts/demo_client.py ensure chase_point
  python Scripts/demo_client.py ensure demo_arena
  python Scripts/demo_client.py status

Endpoints (127.0.0.1:8878):
  GET  /v1/health
  GET  /v1/demos
  GET  /v1/status
  POST /v1/demos/<id>/load   — stop PIE, activate environment, mark ready
  POST /v1/play              — begin PIE (optional)
  POST /v1/stop              — end PIE
"""

from __future__ import annotations

import json
import queue
import sys
import threading
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import urlparse

from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

import unreal

from envs import ENVIRONMENTS, activate, get_environment, list_environments

HOST = "127.0.0.1"
PORT = 8878

_job_queue: queue.Queue = queue.Queue()
_status_lock = threading.Lock()
_status: dict[str, Any] = {
    "server": "ok",
    "state": "idle",  # idle | loading | ready | error | playing
    "demo_id": None,
    "env_id": None,
    "message": "control server started",
    "error": None,
}
_tick_handle = None
_httpd: ThreadingHTTPServer | None = None

# Deferred editor work — never busy-wait inside a slate tick (blocks End Play).
_pending: dict[str, Any] | None = None
_PENDING_WAIT_TICKS = 600  # ~10s at 60 Hz


def _set_status(**kwargs: Any) -> dict[str, Any]:
    with _status_lock:
        _status.update(kwargs)
        snapshot = dict(_status)
    try:
        ctrl = getattr(unreal, "_rlmesh_demo_control", None)
        if isinstance(ctrl, dict):
            ctrl["status"] = snapshot
    except Exception:  # noqa: BLE001
        pass
    return snapshot


def _get_status() -> dict[str, Any]:
    with _status_lock:
        return dict(_status)


def _json_bytes(payload: dict[str, Any], code: int = 200) -> tuple[int, bytes]:
    body = json.dumps(payload, indent=2).encode("utf-8")
    return code, body


def _level_editor() -> Any:
    return unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)


def _is_in_pie() -> bool:
    les = _level_editor()
    if les is None:
        return False
    try:
        return bool(les.is_in_play_in_editor())
    except Exception:  # noqa: BLE001
        return False


def _request_end_play() -> None:
    try:
        les = _level_editor()
        if les is not None:
            les.editor_request_end_play()
            unreal.log("demo_control: requested End Play")
            return
    except Exception as exc:  # noqa: BLE001
        unreal.log_warning(f"demo_control: end play via subsystem failed: {exc}")
    try:
        unreal.EditorLevelLibrary.editor_end_play()
        unreal.log("demo_control: editor_end_play()")
    except Exception as exc:  # noqa: BLE001
        unreal.log_warning(f"demo_control: end play skipped: {exc}")


def _request_begin_play() -> None:
    les = _level_editor()
    if les is None:
        raise RuntimeError("LevelEditorSubsystem unavailable")
    les.editor_request_begin_play()
    unreal.log("demo_control: requested Begin Play")


def _activate_environment(env_key: str) -> dict[str, Any]:
    unreal.log(f"demo_control: activating environment {env_key!r}")
    return activate(env_key)


def _finish_job(reply_q: queue.Queue, ok: bool, payload: dict[str, Any], error: str | None = None) -> None:
    if ok:
        reply_q.put({"ok": True, "status": payload})
    else:
        reply_q.put({"ok": False, "status": payload, "error": error or payload.get("error")})


def _start_pending(kind: str, reply_q: queue.Queue, **kwargs: Any) -> None:
    global _pending
    _pending = {
        "kind": kind,
        "reply": reply_q,
        "waited": 0,
        "phase": "stop" if _is_in_pie() else "run",
        **kwargs,
    }
    if _pending["phase"] == "stop":
        _request_end_play()
        unreal.log(f"demo_control: deferring {kind} until PIE ends")


def _advance_pending() -> None:
    """Drive stop → run across ticks so End Play can complete."""
    global _pending
    if _pending is None:
        return

    kind = _pending["kind"]
    reply_q: queue.Queue = _pending["reply"]
    phase = _pending["phase"]
    _pending["waited"] = int(_pending.get("waited", 0)) + 1

    try:
        if phase == "stop":
            if _is_in_pie():
                if _pending["waited"] >= _PENDING_WAIT_TICKS:
                    raise TimeoutError("timed out waiting for PIE to end")
                # Re-request occasionally in case the first was ignored.
                if _pending["waited"] % 30 == 0:
                    _request_end_play()
                return
            _pending["phase"] = "run"
            _pending["waited"] = 0
            # Fall through into run on the same tick once PIE is clear.

        if _pending["phase"] == "run":
            if kind == "load":
                demo_id = str(_pending["demo_id"])
                demo = get_environment(demo_id)
                if demo is None:
                    raise KeyError(f"unknown environment id={demo_id!r}")
                _set_status(
                    state="loading",
                    demo_id=demo_id,
                    env_id=demo["env_id"],
                    message=f"activating {demo_id}",
                    error=None,
                )
                _activate_environment(demo_id)
                payload = _set_status(
                    state="ready",
                    demo_id=demo_id,
                    env_id=demo["env_id"],
                    message=(
                        f"environment {demo_id} ready; press Play (or POST /v1/play). "
                        f"Expect Serving {demo['env_id']}"
                    ),
                    error=None,
                )
                _finish_job(reply_q, True, payload)
            elif kind == "play":
                if _is_in_pie():
                    # Already playing (e.g. user pressed Play) — treat as success.
                    payload = _set_status(
                        state="playing",
                        message="Already in Play; wait for LogRLMesh Serving …",
                    )
                    _finish_job(reply_q, True, payload)
                else:
                    _request_begin_play()
                    payload = _set_status(
                        state="playing",
                        message="Play requested; wait for LogRLMesh Serving …",
                    )
                    _finish_job(reply_q, True, payload)
            elif kind == "stop":
                payload = _set_status(state="ready", message="Play ended")
                _finish_job(reply_q, True, payload)
            else:
                raise RuntimeError(f"unknown pending kind {kind!r}")
            _pending = None
    except Exception as exc:  # noqa: BLE001
        err = f"{exc}\n{traceback.format_exc()}"
        unreal.log_error(f"demo_control job failed: {exc}")
        payload = _set_status(state="error", message=str(exc), error=err)
        _finish_job(reply_q, False, payload, str(exc))
        _pending = None


def _process_jobs(_delta: float) -> bool:
    """Slate tick: accept one new job when idle; advance deferred stop/run."""
    global _pending
    try:
        if _pending is None:
            job = _job_queue.get_nowait()
            kind = job.get("kind")
            reply_q: queue.Queue = job["reply"]
            try:
                if kind == "load":
                    demo_id = str(job["demo_id"])
                    _set_status(
                        state="loading",
                        demo_id=demo_id,
                        message=f"loading {demo_id}",
                        error=None,
                    )
                    _start_pending("load", reply_q, demo_id=demo_id)
                elif kind == "play":
                    # Always stop first so a prior env's EnvServer dies before begin.
                    _start_pending("play", reply_q)
                elif kind == "stop":
                    _start_pending("stop", reply_q)
                else:
                    raise RuntimeError(f"unknown job kind {kind!r}")
            except Exception as exc:  # noqa: BLE001
                err = f"{exc}\n{traceback.format_exc()}"
                unreal.log_error(f"demo_control job failed: {exc}")
                payload = _set_status(state="error", message=str(exc), error=err)
                _finish_job(reply_q, False, payload, str(exc))
    except queue.Empty:
        pass

    _advance_pending()
    return True  # keep ticking


def _enqueue(kind: str, **kwargs: Any) -> dict[str, Any]:
    reply: queue.Queue = queue.Queue()
    _job_queue.put({"kind": kind, "reply": reply, **kwargs})
    # Block the HTTP worker thread until the editor tick finishes the job.
    result = reply.get(timeout=120.0)
    return result


class _Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt: str, *args: Any) -> None:  # noqa: A003
        unreal.log(f"demo_control: " + (fmt % args))

    def _send(self, code: int, body: bytes, content_type: str = "application/json") -> None:
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self) -> None:  # noqa: N802
        self._send(204, b"")

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path.rstrip("/") or "/"
        if path == "/v1/health":
            code, body = _json_bytes({"ok": True, "service": "rlmesh-demo-control"})
        elif path == "/v1/demos":
            code, body = _json_bytes({"demos": list_environments()})
        elif path == "/v1/status":
            code, body = _json_bytes(_get_status())
        else:
            code, body = _json_bytes({"error": f"not found: {path}"}, 404)
        self._send(code, body)

    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path.rstrip("/") or "/"
        length = int(self.headers.get("Content-Length", "0") or "0")
        if length:
            _ = self.rfile.read(length)

        try:
            if path.startswith("/v1/demos/") and path.endswith("/load"):
                demo_id = path[len("/v1/demos/") : -len("/load")]
                if demo_id not in ENVIRONMENTS:
                    self._send(*_json_bytes({"error": f"unknown demo {demo_id!r}"}, 404))
                    return
                result = _enqueue("load", demo_id=demo_id)
                code = 200 if result.get("ok") else 500
                self._send(*_json_bytes(result, code))
                return
            if path == "/v1/play":
                result = _enqueue("play")
                code = 200 if result.get("ok") else 500
                self._send(*_json_bytes(result, code))
                return
            if path == "/v1/stop":
                result = _enqueue("stop")
                code = 200 if result.get("ok") else 500
                self._send(*_json_bytes(result, code))
                return
            self._send(*_json_bytes({"error": f"not found: {path}"}, 404))
        except Exception as exc:  # noqa: BLE001
            self._send(*_json_bytes({"error": str(exc)}, 500))


def _shutdown_existing(existing: dict[str, Any] | None) -> None:
    global _tick_handle, _httpd, _pending
    if not existing and _httpd is None:
        return
    httpd = (existing or {}).get("httpd", _httpd)
    tick = (existing or {}).get("tick", _tick_handle)
    if httpd is not None:
        try:
            httpd.shutdown()
            httpd.server_close()
        except Exception:  # noqa: BLE001
            pass
    if tick is not None:
        try:
            unreal.unregister_slate_post_tick_callback(tick)
        except Exception:  # noqa: BLE001
            pass
    _httpd = None
    _tick_handle = None
    _pending = None
    try:
        unreal._rlmesh_demo_control = None
    except Exception:  # noqa: BLE001
        pass


def start(*, force: bool = False) -> None:
    """Start the HTTP server. Soft by default so Play does not kill in-flight clients."""
    global _tick_handle, _httpd
    existing = getattr(unreal, "_rlmesh_demo_control", None)
    if (
        not force
        and isinstance(existing, dict)
        and existing.get("httpd") is not None
        and existing.get("port") == PORT
    ):
        unreal.log(f"demo_control already listening on http://{HOST}:{PORT}")
        return

    prior_status = None
    if isinstance(existing, dict):
        prior_status = existing.get("status")
        if not isinstance(prior_status, dict):
            prior_status = None
    _shutdown_existing(existing if isinstance(existing, dict) else None)

    _tick_handle = unreal.register_slate_post_tick_callback(_process_jobs)
    _httpd = ThreadingHTTPServer((HOST, PORT), _Handler)
    thread = threading.Thread(target=_httpd.serve_forever, name="rlmesh-demo-control", daemon=True)
    thread.start()
    if prior_status and prior_status.get("demo_id"):
        restored = dict(prior_status)
        restored["server"] = "ok"
        if restored.get("state") in ("ready", "playing", "loading"):
            restored["state"] = "playing"
            restored["message"] = "Play (control server kept)"
        _set_status(**restored)
    unreal._rlmesh_demo_control = {
        "httpd": _httpd,
        "tick": _tick_handle,
        "port": PORT,
        "status": _get_status(),
    }
    unreal.log(f"demo_control listening on http://{HOST}:{PORT}")
    unreal.log('  GET  /v1/demos  |  POST /v1/demos/<id>/load  |  POST /v1/play  |  GET /v1/status')


# Soft ensure on Play / editor startup. Force reload: pass --reload.
start(force="--reload" in sys.argv)
