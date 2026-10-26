"""Run from the repository root: python scripts/run.py."""

from pathlib import Path
import subprocess, sys

root = Path(__file__).resolve().parents[1]
if not (root / "frontend" / "dist" / "index.html").exists():
    raise SystemExit(
        "Сначала соберите интерфейс: cd frontend && npm ci && npm run build"
    )
subprocess.run(
    [
        sys.executable,
        "-m",
        "uvicorn",
        "backend.app.api:app",
        "--host",
        "127.0.0.1",
        "--port",
        "8000",
        "--no-access-log",
    ],
    cwd=root,
    check=True,
)
