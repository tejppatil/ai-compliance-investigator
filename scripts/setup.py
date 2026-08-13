#!/usr/bin/env python3
"""
One-command local setup.

    python scripts/setup.py            # full setup
    python scripts/setup.py --skip-models   # skip the Ollama model pulls

Does everything needed to go from a fresh clone to a running system:
  1. installs Python dependencies
  2. locates Ollama and pulls the two local models
  3. initialises the local SQLite database
  4. builds + caches the regulatory RAG embedding index
  5. installs frontend npm dependencies

Internet is needed ONCE here, to fetch dependencies and models. After this,
the application runs fully offline — see README "Offline operation".
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from aci.console import enable_utf8_stdout  # noqa: E402

enable_utf8_stdout()

# Windows installs Ollama per-user and doesn't always put it on PATH for
# non-login shells, so check the known install locations too.
OLLAMA_CANDIDATES = [
    Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Ollama" / "ollama.exe",
    Path("C:/Program Files/Ollama/ollama.exe"),
    Path("/usr/local/bin/ollama"),
    Path("/opt/homebrew/bin/ollama"),
]


def say(step: str, msg: str) -> None:
    print(f"[{step}] {msg}", flush=True)


def find_ollama() -> str | None:
    found = shutil.which("ollama")
    if found:
        return found
    for candidate in OLLAMA_CANDIDATES:
        if candidate.exists():
            return str(candidate)
    return None


def run(cmd: list[str], **kwargs) -> int:
    return subprocess.call(cmd, **kwargs)


def install_python_deps() -> None:
    say("1/5", "Installing Python dependencies…")
    code = run([sys.executable, "-m", "pip", "install", "-q", "-r", str(ROOT / "requirements.txt")])
    say("1/5", "Python dependencies installed." if code == 0 else "pip install failed — see output above.")


def setup_models(skip: bool) -> None:
    from aci import config
    if skip:
        say("2/5", "Skipping model pulls (--skip-models). The system will use the deterministic template narrative.")
        return
    ollama = find_ollama()
    if not ollama:
        say("2/5", "Ollama not found. Install it from https://ollama.com/download, then re-run.")
        say("2/5", "The system still works without it — narratives fall back to a deterministic template.")
        return
    for model in (config.LLM_MODEL, config.EMBED_MODEL):
        say("2/5", f"Pulling {model} (first run downloads a few GB)…")
        if run([ollama, "pull", model]) != 0:
            say("2/5", f"Could not pull {model} — continuing; the template fallback still works.")


def init_database() -> None:
    from aci import config, db
    say("3/5", f"Initialising SQLite database at {config.DB_PATH}…")
    db.init_db()
    say("3/5", "Database ready.")


def build_rag_index() -> None:
    from aci.rag.retriever import Retriever
    say("4/5", "Building regulatory RAG embedding index…")
    retriever = Retriever()
    if retriever.ensure_dense_index():
        say("4/5", f"Embedded {len(retriever.kb)} regulatory documents (cached locally; not recomputed on startup).")
    else:
        say("4/5", "Ollama unavailable — retrieval will use the lexical TF-IDF channel only. Still fully functional.")


def install_frontend() -> None:
    npm = shutil.which("npm")
    if not npm:
        say("5/5", "npm not found — skipping frontend install. Install Node.js to use the web console.")
        return
    say("5/5", "Installing frontend dependencies…")
    code = run([npm, "install", "--silent"], cwd=str(ROOT / "frontend"), shell=(os.name == "nt"))
    say("5/5", "Frontend ready." if code == 0 else "npm install failed — see output above.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Set up the AI Compliance Investigator locally.")
    parser.add_argument("--skip-models", action="store_true", help="skip Ollama model downloads")
    args = parser.parse_args()

    print("AI Compliance Investigator — local setup\n" + "=" * 46)
    install_python_deps()
    setup_models(args.skip_models)
    init_database()
    build_rag_index()
    install_frontend()

    print("\n" + "=" * 46)
    print("Setup complete. To run:\n")
    print("  python run_demo.py                 # CLI investigation report")
    print("  python run_demo.py --eval          # evaluation metrics")
    print("  python scripts/start.py            # API + web console together")
    print("\nThe application runs fully offline from here on.")


if __name__ == "__main__":
    main()
