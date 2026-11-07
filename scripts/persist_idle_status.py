#!/usr/bin/env python3
"""Rewrite status.json when the cast pipeline pid is already dead.

A leftover P2P group interface is not a live DHCP wait. dhcp/connecting
with a dead pid becomes error. rtsp/streaming stay as they were so a
watcher can still describe an up group. Does not remove the group or
move a virtual head.
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path


def _pid_alive(pid: str) -> bool:
    if not str(pid).isdigit():
        return False
    try:
        os.kill(int(pid), 0)
    except OSError:
        return False
    return True


def next_status(data: dict, link_up: bool) -> dict | None:
    """Return the replacement status, or None to leave the file alone."""
    if not isinstance(data, dict):
        return None
    phase = str(data.get("phase") or "")
    running = data.get("running") in (True, "true", "1", "yes", 1)
    stale_phase = phase in ("connecting", "dhcp", "rtsp", "streaming", "scanning")
    pid = str(data.get("pid") or "").strip()
    if _pid_alive(pid):
        return None
    if not running and not stale_phase:
        return None
    out = {k: data[k] for k in ("peer", "peerName", "mode") if data.get(k)}
    out["ts"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    out["running"] = False
    out["pid"] = None
    if link_up:
        if phase in ("dhcp", "connecting"):
            out["phase"] = "error"
            out["message"] = "Cast process exited before the sink got an IP"
        else:
            if phase not in ("rtsp", "streaming"):
                phase = "dhcp"
                data = dict(data)
                data["message"] = "P2P up; waiting for sink IP / RTSP"
            out["phase"] = phase
            out["message"] = data.get("message") or "P2P up; waiting for sink IP / RTSP"
    else:
        out["phase"] = "idle"
        out["message"] = "Idle"
    return out


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print("usage: persist_idle_status.py STATUS_FILE link_up", file=sys.stderr)
        return 2
    path, link = argv[1], argv[2]
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return 0
    out = next_status(data, link == "true")
    if out is None:
        return 0
    Path(path).write_text(json.dumps(out, separators=(",", ":")) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
