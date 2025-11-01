#!/usr/bin/env python3
"""Container entrypoint: wait DB, migrate, bootstrap, exec CMD."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from socket import AF_INET, SOCK_STREAM, socket


def _env_bool(name: str, default: bool | None = None) -> bool:
    """Parse boolean-like env values: 1/true/yes/on."""
    val = os.getenv(name)
    if val is None:
        if default is None:
            raise SystemExit(f"[entrypoint] {name} must be set")
        return default
    return val.strip().lower() in {"1", "true", "yes", "on"}


def wait_for_db(host: str, port: int = 5432, timeout: int = 60) -> None:
    """Wait until TCP host:port is reachable or timeout."""
    start = time.time()
    while True:
        try:
            with socket(AF_INET, SOCK_STREAM) as s:
                s.settimeout(2)
                s.connect((host, port))
            elapsed = time.time() - start
            print(f"[entrypoint] DB ready in {elapsed:.1f}s ({host}:{port})")
            return
        except OSError:
            if time.time() - start > timeout:
                raise SystemExit(f"[entrypoint] DB {host}:{port} unreachable after {timeout}s")
            time.sleep(1)


def run(cmd: list[str]) -> None:
    """Run a subprocess and print captured output on failure."""
    print(f"[entrypoint] $ {' '.join(cmd)}")
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode:
        print(f"[entrypoint] command failed: {' '.join(cmd)} (exit {res.returncode})")
        if res.stdout:
            print("[stdout]")
            print(res.stdout)
        if res.stderr:
            print("[stderr]")
            print(res.stderr)
        sys.exit(1)

def migrate_and_bootstrap() -> None:
    """Apply migrations; optionally run bootstrap script."""
    run(["alembic", "upgrade", "head"])
    if _env_bool("BOOTSTRAP_FLAG"):
        run(["python", "-m", "app.scripts.bootstrap"])
    else:
        print("[entrypoint] BOOTSTRAP_FLAG is false → skip bootstrap")


def main() -> int:
    parser = argparse.ArgumentParser(description="Container entrypoint for API")
    _, cmd = parser.parse_known_args()
    if not cmd:
        raise SystemExit("[entrypoint] no CMD provided")

    db_host_key = next((k for k in os.environ if k.endswith("DB_HOST")), None)
    if not db_host_key:
        raise SystemExit("[entrypoint] DB_HOST env var not found (no *DB_HOST key)")
    db_host = os.getenv(db_host_key)
    if not db_host:
        raise SystemExit(f"[entrypoint] {db_host_key} is set but empty")

    wait_for_db(db_host, 5432, 60)
    migrate_and_bootstrap()

    if os.getenv("DEBUG") == "true":
        uvicorn_args = cmd[cmd.index("uvicorn")+1:]  # ['api.http.main:app', '--host', '0.0.0.0', '--port', '8000']

        cmd = [
            "python",
            "-Xfrozen_modules=off",
            "-m", "debugpy",
            "--listen", "0.0.0.0:5678",
            "--wait-for-client",
            "-m", "uvicorn",
            *uvicorn_args,
        ]
        print(f"[entrypoint] execvp → {' '.join(cmd)}")
    os.execvp(cmd[0], cmd)

    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
