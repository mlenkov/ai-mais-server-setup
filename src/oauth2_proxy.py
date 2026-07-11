import os
import pathlib
import tempfile

from . import utils

OAUTH2_PROXY_VERSION = "v7.15.3"
BINARY_PATH = pathlib.Path("/usr/local/bin/oauth2-proxy")
UNIT_PATH = pathlib.Path("/etc/systemd/system/oauth2-proxy.service")
AUTH_EMAILS_PATH = pathlib.Path("/etc/oauth2-proxy/authenticated-emails.txt")

DOWNLOAD_URL = (
    "https://github.com/oauth2-proxy/oauth2-proxy/releases/download/"
    f"{OAUTH2_PROXY_VERSION}/"
    f"oauth2-proxy-{OAUTH2_PROXY_VERSION}.linux-amd64.tar.gz"
)

UNIT_CONTENT = """\
[Unit]
Description=OAuth2 Proxy
After=network.target

[Service]
Type=simple
User=oauth2-proxy
EnvironmentFile=/opt/secrets/hermes.env
ExecStart=/usr/local/bin/oauth2-proxy \\
  --provider=oidc \\
  --oidc-issuer-url=https://oauth.yandex.ru \\
  --login-url=https://oauth.yandex.ru/authorize \\
  --redeem-url=https://oauth.yandex.ru/token \\
  --profile-url=https://login.yandex.ru/info \\
  --scope="login:email login:info" \\
  --client-id=${YANDEX_CLIENT_ID} \\
  --client-secret=${YANDEX_CLIENT_SECRET} \\
  --cookie-secret=${OAUTH2_PROXY_COOKIE_SECRET} \\
  --cookie-secure=true \\
  --cookie-domain=ai.mais.agency \\
  --upstream=http://127.0.0.1:8080 \\
  --http-address=127.0.0.1:4180 \\
  --set-xauthrequest=true \\
  --pass-access-token=false \\
  --email-domain=* \\
  --authenticated-emails-file=/etc/oauth2-proxy/authenticated-emails.txt

Restart=always
RestartSec=5
ProtectSystem=strict
PrivateTmp=yes
NoNewPrivileges=yes
PrivateDevices=yes

[Install]
WantedBy=multi-user.target
"""


def install_oauth2_proxy():
    if BINARY_PATH.exists():
        result = utils.shell(f"{BINARY_PATH} --version 2>&1", check=False, capture=True)
        if OAUTH2_PROXY_VERSION.lstrip("v") in result.stdout:
            print(f"  oauth2-proxy {OAUTH2_PROXY_VERSION} already installed")
            return
        print(f"  Upgrading oauth2-proxy...")

    print(f"  Downloading oauth2-proxy {OAUTH2_PROXY_VERSION}...")
    with tempfile.TemporaryDirectory() as tmpdir:
        archive = os.path.join(tmpdir, "oauth2-proxy.tar.gz")
        utils.download_file(DOWNLOAD_URL, archive)
        utils.shell(f"tar xzf {archive} -C {tmpdir}")
        bin_src = os.path.join(
            tmpdir,
            f"oauth2-proxy-{OAUTH2_PROXY_VERSION}.linux-amd64",
            "oauth2-proxy",
        )
        if not os.path.exists(bin_src):
            bin_src = os.path.join(tmpdir, "oauth2-proxy")
        utils.shell(f"mv {bin_src} {BINARY_PATH}")
        utils.shell(f"chmod +x {BINARY_PATH}")

    print(f"  oauth2-proxy installed to {BINARY_PATH}")


def create_user():
    if utils.user_exists("oauth2-proxy"):
        print("  User oauth2-proxy already exists")
        return
    utils.shell(
        "useradd --system --no-create-home "
        "--shell /usr/sbin/nologin oauth2-proxy"
    )
    print("  User oauth2-proxy created")


def configure_service():
    utils.file_write(UNIT_PATH, UNIT_CONTENT)

    emails_src = (
        pathlib.Path(__file__).resolve().parent.parent
        / "configs"
        / "authenticated-emails.txt"
    )
    if emails_src.exists():
        emails_content = emails_src.read_text()
    else:
        emails_content = "# Add one email per line\n"

    utils.file_write(AUTH_EMAILS_PATH, emails_content)

    utils.systemd_reload()
    utils.systemd_enable_start("oauth2-proxy")
    print("  OAuth2-Proxy service configured")
