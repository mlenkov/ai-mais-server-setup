import pathlib

from . import utils

HERMES_USER = "hermes"
HERMES_HOME = pathlib.Path(f"/home/{HERMES_USER}")
HERMES_VENV = HERMES_HOME / ".hermes" / "hermes-agent" / "venv" / "bin" / "hermes"
HERMES_LINK = pathlib.Path("/usr/local/bin/hermes")
HERMES_ENV_FILE = HERMES_HOME / ".hermes" / ".env"
UNIT_PATH = pathlib.Path("/etc/systemd/system/hermes-agent.service")

UNIT_CONTENT = """\
[Unit]
Description=Hermes Agent Dashboard
After=network.target

[Service]
Type=simple
User=hermes
ExecStart=/home/hermes/.hermes/hermes-agent/venv/bin/hermes dashboard --port 9119 --host 127.0.0.1

Restart=always
RestartSec=5
ProtectSystem=strict
PrivateTmp=yes
NoNewPrivileges=yes

[Install]
WantedBy=multi-user.target
"""


def create_user():
    if utils.user_exists(HERMES_USER):
        print(f"  User {HERMES_USER} already exists")
        return
    utils.shell(
        f"useradd --system --create-home --shell /bin/bash {HERMES_USER}"
    )
    print(f"  User {HERMES_USER} created")


def install_hermes():
    if HERMES_VENV.exists():
        print(f"  Hermes already installed at {HERMES_VENV}")
        return

    print("  Installing Hermes Agent (this may take a while)...")
    cmd = (
        f"su - {HERMES_USER} -c "
        f'"curl -fsSL https://hermes-agent.nousresearch.com/install.sh '
        f'| bash -s -- --skip-browser"'
    )
    utils.shell(cmd, timeout=600)

    if not HERMES_LINK.exists() and HERMES_VENV.exists():
        utils.shell(f"ln -sf {HERMES_VENV} {HERMES_LINK}")
        print(f"  Symlink created: {HERMES_LINK}")

    print("  Hermes Agent installed")


def configure_provider(api_key):
    dot_hermes = HERMES_HOME / ".hermes"
    dot_hermes.mkdir(parents=True, exist_ok=True)
    utils.shell(f"chown {HERMES_USER}:{HERMES_USER} {dot_hermes}")

    if HERMES_ENV_FILE.exists():
        existing = HERMES_ENV_FILE.read_text()
        if f"OPENCODE_ZEN_API_KEY={api_key}" in existing:
            print("  OpenCode Zen API key already configured")
            _ensure_model()
            return

    utils.file_write(HERMES_ENV_FILE, f"OPENCODE_ZEN_API_KEY={api_key}\n")
    utils.shell(f"chown {HERMES_USER}:{HERMES_USER} {HERMES_ENV_FILE}")
    print(f"  OpenCode Zen API key written")

    _ensure_model()


def _ensure_model():
    result = utils.shell(
        f"su - {HERMES_USER} -c "
        f"'hermes config set model opencode-zen/deepseek-v4-flash-free'",
        check=False,
        capture=True,
        timeout=60,
    )
    if result.returncode == 0:
        print("  Model set to opencode-zen/deepseek-v4-flash-free")
    else:
        err = result.stderr.strip() if result.stderr else ""
        print(f"  Could not set model: {err}")


def configure_service():
    utils.file_write(UNIT_PATH, UNIT_CONTENT)
    utils.systemd_reload()
    utils.systemd_enable_start("hermes-agent")
    print("  Hermes Agent service configured")
