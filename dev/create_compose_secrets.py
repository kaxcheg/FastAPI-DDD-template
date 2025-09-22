#!/usr/bin/env python3
"""Generate secret files for docker compose using yaml secrets section."""

import argparse
import getpass
import yaml
from pathlib import Path

def parse_dotenv(path: Path) -> dict[str, str]:
    """Return key-value pairs from .env like file (KEY=VALUE per line)."""

    data: dict[str, str] = {}
    for line in path.read_text().splitlines():
        if not line or line.lstrip().startswith("#"):
            continue
        if "=" not in line:
            continue
        k, v = line.split("=", 1)
        data[k.strip()] = v.strip()
    return data


def main() -> None:
    """Create secret files interactively or from yaml file."""

    parser = argparse.ArgumentParser()
    parser.add_argument("--from-file", help=".env with KEY=VALUE secrets")
    parser.add_argument("--yml", "-y", default="./docker-compose.yml", help="Compose manifest file")
    parser.add_argument("--out-dir", "-o", default="./secrets", help="Output dir")
    args = parser.parse_args()

    with open(args.yml, "r") as fp:
        compose_data = yaml.safe_load(fp)
        secrets = list(compose_data.get('secrets', {}).keys())

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    predefined: dict[str, str] = (
        parse_dotenv(Path(args.from_file)) if args.from_file else {}
    )

    for name in secrets:
        value = predefined.get(name) or getpass.getpass(f"Secret '{name}': ").strip()

        secret_file = out_dir / name
        if secret_file.exists():
            secret_file.chmod(0o640)
        secret_file.write_text(value)
        secret_file.chmod(0o400)

    print(f"[create_compose_secrets] wrote {len(secrets)} secrets to {out_dir}")


if __name__ == "__main__":  # pragma: no cover
    main()
