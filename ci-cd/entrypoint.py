#!/usr/bin/env python3
"""Container entrypoint: validate env, wait DB, migrate, create admin, exec CMD."""

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from socket import AF_INET, SOCK_STREAM, socket
from typing import TypedDict


class ConfigField(TypedDict):
    name: str
    is_secret: bool


def validate_env(configs: list[ConfigField], secrets_dir: Path) -> None:
    """Exit if public env vars unset or secret files missing."""
    missing = [
        c["name"]
        for c in configs
        if not c["is_secret"] and os.environ.get(c["name"]) is None
    ]
    missing_secrets = [
        c["name"]
        for c in configs
        if c["is_secret"] and not (secrets_dir / c["name"].lower()).is_file()
    ]
    if missing or missing_secrets:
        msg = []
        if missing:
            msg.append("vars: " + ", ".join(missing))
        if missing_secrets:
            msg.append("secret files: " + ", ".join(missing_secrets))
        sys.exit("[entrypoint] missing " + "; ".join(msg))


def wait_for_db(host: str, port: int, timeout: int = 30) -> None:
    """Wait until TCP host:port is reachable or timeout."""
    start = time.time()
    while True:
        try:
            with socket(AF_INET, SOCK_STREAM) as s:
                s.settimeout(2)
                s.connect((host, port))
                print(f"[entrypoint] DB ready in {time.time() - start:.1f}s")
                return
        except OSError:
            if time.time() - start > timeout:
                sys.exit(f"[entrypoint] DB {host}:{port} unreachable")
            time.sleep(1)


def run_cmd(cmd: list[str]) -> None:
    """Run subprocess and exit on failure."""
    res = subprocess.run(cmd, stdout=sys.stdout, stderr=sys.stderr)
    if res.returncode:
        sys.exit(f"[entrypoint] command failed: {' '.join(cmd)}")


def bootstrap(cfg: list[ConfigField]) -> None:
    """Run migrations and admin creation after DB is up."""
    host_name = next((c["name"] for c in cfg if c["name"].endswith("POSTGRES_HOST")), None)
    if not host_name:
        raise RuntimeError("[entrypoint] POSTGRES_HOST var not found")

    host = os.getenv(host_name)
    if not host:
        raise RuntimeError(f"[entrypoint] {host_name} is not set")

    wait_for_db(host, 5432, 60)
    run_cmd(["alembic", "upgrade", "head"])
    run_cmd(["python", "-m", "app.scripts.create_admin"])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config-fields", "-c", default="config_fields.json")
    parser.add_argument("--secrets-dir", "-s", default="/run/secrets")
    args, cmd = parser.parse_known_args()

    with open(args.config_fields, "r", encoding="utf-8") as fp:
        cfg: list[ConfigField] = json.load(fp)

    validate_env(cfg, Path(args.secrets_dir))
    bootstrap(cfg)

    if not cmd:
        sys.exit("[entrypoint] no CMD provided")

    os.execvp(cmd[0], cmd)


if __name__ == "__main__":  # pragma: no cover
    main()
