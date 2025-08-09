#!/usr/bin/env python3

"""Generate JSON with env var names used by BaseConfig (Python 3.12)."""

import argparse
import json
from pathlib import Path
from typing import TypedDict, cast, Sequence

from pydantic import SecretStr

from app.config import APP_PREFIX, BaseConfig


class FieldDict(TypedDict):
    """Descriptor for a single environment variable."""

    name: str
    is_secret: bool

def get_config_fields() -> tuple[list[str], list[str]]:
    """Collect secret and public env var names from ``BaseConfig``.

    Returns:
        tuple[list[str], list[str]]: secrets, then public vars.
    """

    secrets = [
        f"{APP_PREFIX}{(field.alias or name).upper()}"
        for name, field in BaseConfig.model_fields.items()
        if field.annotation is SecretStr
    ]
    env_vars = [
        f"{APP_PREFIX}{(field.alias or name).upper()}"
        for name, field in BaseConfig.model_fields.items()
        if field.annotation is not SecretStr
    ]
    return sorted(secrets), sorted(env_vars)


def build_field_list(secrets: Sequence[str], env_vars: Sequence[str]) -> list[FieldDict]:
    """Return combined list preserving ``FieldDict`` typing."""

    public_entries = [cast(FieldDict, {"name": n, "is_secret": False}) for n in env_vars]
    secret_entries = [cast(FieldDict, {"name": n, "is_secret": True}) for n in secrets]
    return public_entries + secret_entries


def main() -> None:
    """CLI entry point that writes ``deploy/config_fields.json``."""

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output", "-o", default="deploy/config_fields.json", help="Path to output JSON file."
    )
    args = parser.parse_args()

    secret_envs, public_envs = get_config_fields()
    all_fields = build_field_list(secret_envs, public_envs)

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(all_fields, indent=4, ensure_ascii=False), encoding="utf-8")
    print(f"[generate_config_fields] wrote {out} (secrets={len(secret_envs)} env={len(public_envs)})")


if __name__ == "__main__":  # pragma: no cover
    main()
