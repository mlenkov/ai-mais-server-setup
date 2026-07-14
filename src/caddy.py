import pathlib

from . import utils

CADDYFILE_PATH = pathlib.Path("/etc/caddy/Caddyfile")

CADDYFILE_CONTENT = (pathlib.Path(__file__).resolve().parent.parent / "configs" / "Caddyfile").read_text()


def install_caddy():
    if utils.is_installed_pkg("caddy"):
        print("  Caddy already installed")
        return
    print("  Installing Caddy via apt...")
    utils.shell("apt install -y caddy")
    print("  Caddy installed")


def configure_caddy():
    existing = utils.file_read(CADDYFILE_PATH)
    if existing and existing.strip() == CADDYFILE_CONTENT.strip():
        print("  Caddyfile already up to date")
        return
    utils.file_write(CADDYFILE_PATH, CADDYFILE_CONTENT)
    print("  Caddyfile written")


def enable_caddy():
    utils.systemd_reload()
    utils.systemd_enable_start("caddy")
