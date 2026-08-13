#!/usr/bin/env python3
"""
Start the API and the web console together.

    python scripts/start.py              # both, and open the browser
    python scripts/start.py --api-only   # just the REST API

Ctrl-C stops both. Nothing here reaches the public internet — the API talks
only to the local SQLite file and (optionally) to Ollama on localhost.
"""
from __future__ import annotations

import argparse
import os
import shutil
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from aci.console import enable_utf8_stdout  # noqa: E402

enable_utf8_stdout()

# Not 8000: the Ollama desktop app binds 8000 on Windows, and this project
# depends on Ollama, so that port is a guaranteed collision.
API_PORT = int(os.environ.get("ACI_API_PORT", "8077"))
WEB_PORT = int(os.environ.get("ACI_WEB_PORT", "5173"))


def wait_for(url: str, timeout: float = 60.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            urllib.request.urlopen(url, timeout=2)
            return True
        except (urllib.error.URLError, OSError):
            time.sleep(0.5)
    return False


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the AI Compliance Investigator locally.")
    parser.add_argument("--api-only", action="store_true", help="do not start the web console")
    parser.add_argument("--no-browser", action="store_true", help="do not open a browser window")
    args = parser.parse_args()

    procs: list[subprocess.Popen] = []
    try:
        print(f"Starting API on http://127.0.0.1:{API_PORT} …")
        procs.append(subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "aci.api.app:app", "--host", "127.0.0.1", "--port", str(API_PORT)],
            cwd=str(ROOT),
        ))
        if not wait_for(f"http://127.0.0.1:{API_PORT}/api/dashboard"):
            print("API did not come up in time — check the output above.")
            return
        print(f"API ready.  Docs: http://127.0.0.1:{API_PORT}/docs")

        if not args.api_only:
            npm = shutil.which("npm")
            if not npm:
                print("npm not found — running API only. Install Node.js for the web console.")
            else:
                print(f"Starting web console on http://localhost:{WEB_PORT} …")
                env = {**os.environ, "VITE_API_BASE": f"http://localhost:{API_PORT}"}
                procs.append(subprocess.Popen(
                    [npm, "run", "dev", "--", "--port", str(WEB_PORT)],
                    cwd=str(ROOT / "frontend"), env=env, shell=(os.name == "nt"),
                ))
                if wait_for(f"http://localhost:{WEB_PORT}") and not args.no_browser:
                    webbrowser.open(f"http://localhost:{WEB_PORT}")

        print("\nRunning. Press Ctrl-C to stop.")
        while True:
            time.sleep(1)
            for p in procs:
                if p.poll() is not None:
                    print(f"A process exited (code {p.returncode}); shutting down.")
                    return
    except KeyboardInterrupt:
        print("\nStopping…")
    finally:
        for p in procs:
            if p.poll() is None:
                p.terminate()
        for p in procs:
            try:
                p.wait(timeout=5)
            except subprocess.TimeoutExpired:
                p.kill()


if __name__ == "__main__":
    main()
