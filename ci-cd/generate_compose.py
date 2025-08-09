#!/usr/bin/env python3
"""Generate docker-compose.yml from template and config_fields.json."""

import argparse
import json
from pathlib import Path
from typing import Any, TypedDict

import yaml


class ConfigField(TypedDict):
    name: str
    is_secret: bool


def env_to_secret(env: str) -> str:
    """Convert ENV_VAR to lowercase secret filename."""
    return env.lower()


def build_compose(image: str, cfg: list[ConfigField], tpl_path: str) -> dict[str, Any]:
    """Return compose-dict with wired env vars and secrets."""
    with open(tpl_path, encoding="utf-8") as fp:
        compose: dict[str, Any] = json.load(fp)

    pg_admin_sec = "postgres_admin_secret"

    app_env: dict[str, str] = {}
    db_env = {"POSTGRES_PASSWORD_FILE": f"/run/secrets/{pg_admin_sec}"}
    db_bootstrap_env = {"DB_ADMIN_PWD_FILE": f"/run/secrets/{pg_admin_sec}"}

    app_secrets: list[dict[str, str]] = []
    db_secrets = [{"source": pg_admin_sec, "target": pg_admin_sec}]
    db_bootstrap_secret = [{"source": pg_admin_sec, "target": pg_admin_sec}]
    all_secrets: dict[str, dict[str, str]] = {pg_admin_sec: {"file": f"./secrets/{pg_admin_sec}"}}

    uvicorn_port: str | None = None

    for field in cfg:
        name = field["name"]

        if field["is_secret"]:
            sec = env_to_secret(name)
            all_secrets.setdefault(sec, {"file": f"./secrets/{sec}"})
            app_secrets.append({"source": sec, "target": sec})
            if name.endswith("_POSTGRES_USER_SECRET"):
                db_bootstrap_env["DB_USER_PWD_FILE"] = f"/run/secrets/{sec}"
                db_bootstrap_secret.append({"source": sec, "target": sec})
            continue

        if "POSTGRES" in name and "POSTGRES_DRIVER" not in name:
            if name.endswith("_POSTGRES_DB"):
                db_env["POSTGRES_DB"] = f"${{{name}}}"
                db_bootstrap_env["DB_NAME"] = f"${{{name}}}"
            elif name.endswith("_POSTGRES_USER"):
                db_bootstrap_env["DB_USER"] = f"${{{name}}}"

        app_env[name] = f"${{{name}}}"

        if name.endswith("_UVICORN_PORT"):
            uvicorn_port = f"${{{name}}}"
    
    if uvicorn_port is None:
        raise ValueError("No *_UVICORN_PORT found in config_fields.json")
        
    compose["services"]["db"]["environment"].update(db_env)
    compose["services"]["db"]["secrets"] = db_secrets

    compose["services"]["db-bootstrap"]["environment"].update(db_bootstrap_env)
    compose["services"]["db-bootstrap"]["secrets"] = db_bootstrap_secret

    compose["services"]["app"]["image"] = image
    compose["services"]["app"]["environment"] = app_env
    compose["services"]["app"]["secrets"] = app_secrets
    compose["services"]["app"]["ports"] = [f"{uvicorn_port}:{uvicorn_port}"]
    compose["services"]["app"]["entrypoint"] = [
        "python",
        "./entrypoint.py",
        "--config-fields",
        "./config_fields.json",
        "uvicorn",
        "app.interface.http.main:app",
        "--host",
        "0.0.0.0",
        "--port",
        uvicorn_port,
    ]

    compose["secrets"] = all_secrets
    return compose


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--image", default="myapp:1.0.0")
    parser.add_argument("-c", "--config-fields", default="deploy/config_fields.json")
    parser.add_argument("-t", "--template", default="./ci-cd/compose.tpl.json")
    parser.add_argument("-o", "--output", default="deploy/docker-compose.yml")
    args, _ = parser.parse_known_args()

    with open(args.config_fields, encoding="utf-8") as fp:
        cfg: list[ConfigField] = json.load(fp)

    compose_dict = build_compose(args.image, cfg, args.template)

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(yaml.safe_dump(compose_dict, sort_keys=False))
    print(f"[generate_compose] wrote {out}")


if __name__ == "__main__":  # pragma: no cover
    main()
