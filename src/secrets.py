import sys
import pathlib
import secrets

ENV_PATH = pathlib.Path("/opt/secrets/hermes.env")


def _parse_env(path):
    if not path.exists():
        return {}
    env = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            key, _, val = line.partition("=")
            env[key.strip()] = val.strip()
    return env


def validate_secrets():
    env = _parse_env(ENV_PATH)

    if not env:
        print("  No secrets file found at /opt/secrets/hermes.env")
        print("  Hermes provider config: skip (configure later)")
        print("  Yandex-Auth: configure manually in /etc/systemd/system/yandex-auth.service")
        return {}

    print(f"  Found {len(env)} keys in {ENV_PATH}")

    if not env.get("YANDEX_CLIENT_ID"):
        print("  YANDEX_CLIENT_ID not set — configure yandex-auth manually")
    if not env.get("OPENCODE_ZEN_API_KEY"):
        print("  OPENCODE_ZEN_API_KEY not set — Hermes will not configure provider")

    print(f"  Secrets validated")
    return env
