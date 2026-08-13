"""
Console output helper.

Windows terminals default to a legacy codepage (cp1252) that cannot encode
the arrows, rupee signs and section marks used in the investigation report —
printing one raises UnicodeEncodeError mid-report and kills the process.
Every CLI entry point calls enable_utf8_stdout() before printing.
"""
from __future__ import annotations

import io
import sys


def enable_utf8_stdout() -> None:
    for name in ("stdout", "stderr"):
        stream = getattr(sys, name, None)
        if stream is None or not hasattr(stream, "buffer"):
            continue
        encoding = (getattr(stream, "encoding", "") or "").lower()
        if encoding != "utf-8":
            setattr(sys, name, io.TextIOWrapper(stream.buffer, encoding="utf-8", errors="replace"))
