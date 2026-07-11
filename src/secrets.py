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


def _append_to_env(path, key, value):
    with open(path, "a") as f:
        f.write(f"\n{key}={value}\n")
    print(f"  Appended {key} to {path}")


def validate_secrets():
    env = _parse_env(ENV_PATH)

    required = ["YANDEX_CLIENT_ID", "YANDEX_CLIENT_SECRET", "OPENCODE_ZEN_API_KEY"]
    missing = [k for k in required if not env.get(k)]

    if missing:
        print(f"  Missing required secrets in {ENV_PATH}: {', '.join(missing)}")
        print(f"  Please add them and re-run.")
        sys.exit(1)

    if not env.get("OAUTH2_PROXY_COOKIE_SECRET"):
        print(f"  Generating OAUTH2_PROXY_COOKIE_SECRET...")
        secret = secrets.token_urlsafe(32)[:43]
        _append_to_env(ENV_PATH, "OAUTH2_PROXY_COOKIE_SECRET", secret)
        env["OAUTH2_PROXY_COOKIE_SECRET"] = secret
        print(f"  OAUTH2_PROXY_COOKIE_SECRET generated")
    else:
        print(f"  OAUTH2_PROXY_COOKIE_SECRET already set")

    print(f"  All secrets validated")
    return env
