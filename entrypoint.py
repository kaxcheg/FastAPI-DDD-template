#!/usr/bin/env python3
"""Container entrypoint: wait DB, migrate, bootstrap, exec CMD."""

import argparse
import os
import subprocess
import sys
import time
from socket import AF_INET, SOCK_STREAM, socket


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


def bootstrap() -> None:
    """Run migrations after DB is up."""
    run_cmd(["python", "-m", "app.scripts.bootstrap"])

def main() -> int:
    parser = argparse.ArgumentParser()
    _, cmd = parser.parse_known_args()
    
    if not cmd:
            sys.exit("[entrypoint] no CMD provided")
    
    db_host_key = next((key for key in os.environ if key.endswith("DB_HOST")), None)
    # db_port_key = next((key for key in os.environ if key.endswith("DB_PORT")), None)

    if not db_host_key:
        raise RuntimeError("[entrypoint] DB_HOST var not found")

    host = os.getenv(db_host_key)
    if not host:
        raise RuntimeError(f"[entrypoint] {db_host_key} is not set")


    # if not db_port_key:
    #     port = 5432
    # else:
    #     port = os.getenv(db_port_key, 5432)

    wait_for_db(host, 5432, 60)
    run_cmd(["alembic", "upgrade", "head"])

    bootstrap_flag = os.getenv("FASTAPI_DDD_TEMPLATE_BOOTSTRAP_FLAG")
    if bootstrap_flag is None:
        sys.exit("[entrypoint] FASTAPI_DDD_TEMPLATE_BOOTSTRAP_FLAG must be set")

    if not bootstrap_flag:
        print("[entrypoint] Bootstrap flag is false. Proceeding without bootstrap.")
        sys.exit(0)
    else:
        bootstrap()

    os.execvp(cmd[0], cmd)


if __name__ == "__main__":  # pragma: no cover
    main()
