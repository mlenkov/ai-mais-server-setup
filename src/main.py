import sys

from . import utils
from . import secrets
from . import caddy
from . import oauth2_proxy
from . import hermes


def main():
    print(r"""
    ╔══════════════════════════════════════════╗
    ║     AI Mais Server Setup                 ║
    ║     Caddy -> OAuth2-Proxy -> Hermes      ║
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

    utils.step_header(3, "OAuth2-Proxy Installation")
    oauth2_proxy.install_oauth2_proxy()
    oauth2_proxy.create_user()
    oauth2_proxy.configure_service()

    utils.step_header(4, "Hermes Agent Installation")
    hermes.create_user()
    hermes.install_hermes()
    hermes.configure_provider(env.get("OPENCODE_ZEN_API_KEY", ""))
    hermes.configure_service()

    print()
    print("=" * 60)
    print("  Setup Complete!")
    print()
    print("  Caddy:       ai.mais.agency:443")
    print("  OAuth2:      127.0.0.1:4180")
    print("  Hermes:      127.0.0.1:8080")
    print()
    print("  Logs:")
    print("  journalctl -u caddy -f")
    print("  journalctl -u oauth2-proxy -f")
    print("  journalctl -u hermes-agent -f")
    print("=" * 60)
    print()


if __name__ == "__main__":
    main()
