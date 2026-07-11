import subprocess
import os
import sys
import pathlib
import urllib.request


def require_root():
    if os.geteuid() != 0:
        print("  This script must be run as root (sudo).", file=sys.stderr)
        sys.exit(1)


def shell(cmd, check=True, capture=True, timeout=None):
    print(f"  $ {cmd}")
    result = subprocess.run(
        cmd,
        shell=True,
        capture_output=capture,
        text=True,
        timeout=timeout,
    )
    if check and result.returncode != 0:
        print(f"  Command failed with exit code {result.returncode}")
        if result.stderr:
            print(f"  stderr: {result.stderr.strip()}")
        sys.exit(result.returncode)
    return result


def is_installed_pkg(name):
    result = shell(f"dpkg -l {name} 2>/dev/null | grep -q '^ii'", check=False, capture=False)
    return result.returncode == 0


def is_binary_version(bin_path, expected_version):
    if not os.path.isfile(bin_path):
        return False
    result = shell(f"{bin_path} --version 2>&1", check=False, capture=True)
    if result.returncode != 0:
        return False
    return expected_version in result.stdout.strip()


def is_systemd_running(unit):
    result = shell(f"systemctl is-active {unit} 2>/dev/null", check=False, capture=True)
    return result.stdout.strip() == "active"


def is_systemd_enabled(unit):
    result = shell(f"systemctl is-enabled {unit} 2>/dev/null", check=False, capture=True)
    return result.stdout.strip() == "enabled"


def systemd_enable_start(unit):
    if not is_systemd_enabled(unit):
        shell(f"systemctl enable {unit}")
    if not is_systemd_running(unit):
        shell(f"systemctl start {unit}")
    else:
        print(f"  {unit} already running")


def systemd_reload():
    shell("systemctl daemon-reload")


def file_write(path, content, mode=0o644):
    p = pathlib.Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(content)
    tmp.chmod(mode)
    tmp.rename(p)
    print(f"  Wrote {p}")


def file_read(path):
    p = pathlib.Path(path)
    if p.exists():
        return p.read_text().strip()
    return None


def download_file(url, dest):
    print(f"  Downloading {url}")
    urllib.request.urlretrieve(url, dest)
    print(f"  Downloaded to {dest}")


def user_exists(name):
    result = shell(f"id {name} 2>/dev/null", check=False, capture=True)
    return result.returncode == 0


def step_header(num, title):
    print()
    print("=" * 60)
    print(f"  TASK {num}: {title}")
    print("=" * 60)
