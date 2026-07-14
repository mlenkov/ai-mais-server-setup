import sys

from . import utils
from . import secrets
from . import caddy
from . import hermes


def main():
    print(r"""
    ╔══════════════════════════════════════════╗
    ║     AI Mais Server Setup                 ║
    ║     Caddy -> Yandex-Auth -> Hermes       ║
    ╚══════════════════════════════════════════╝
    """)

    utils.require_root()

    env = secrets.validate_secrets()

    utils.step_header(1, "Secrets Validation")
    print("  (done above)")

    utils.step_header(2, "Caddy Installation")
    caddy.install_caddy()
    caddy.configure_caddy()
    caddy.enable_caddy()

    utils.step_header(3, "Hermes Agent Installation")
    hermes.create_user()
    hermes.install_hermes()

    api_key = env.get("OPENCODE_ZEN_API_KEY", "")
    if api_key:
        hermes.configure_provider(api_key)
    else:
        print("  No OPENCODE_ZEN_API_KEY set — skip provider config")
        print("  Configure later in /home/hermes/.hermes/.env")

    hermes.configure_service()

    print()
    print("=" * 60)
    print("  Setup Complete!")
    print()
    print("  Caddy:       ai.mais.agency:443")
    print("  Yandex-Auth: 127.0.0.1:4180")
    print("  Hermes:      127.0.0.1:9119")
    print()
    print("  Logs:")
    print("  journalctl -u caddy -f")
    print("  journalctl -u yandex-auth -f")
    print("  journalctl -u hermes-agent -f")
    print("=" * 60)
    print()


if __name__ == "__main__":
    main()
