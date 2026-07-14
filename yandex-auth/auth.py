#!/usr/bin/env python3
"""Minimal OAuth2 auth handler for Yandex OAuth + nginx auth_request."""

import http.server
import json
import os
import secrets
import urllib.parse
import urllib.request
import ssl
import hashlib
import hmac
import base64
import time
import logging

CONFIG = {
    "client_id": os.environ.get("YANDEX_CLIENT_ID", "6d77c0f2bcdc45929b36f0e94f867a46"),
    "client_secret": os.environ.get("YANDEX_CLIENT_SECRET", "c15e31a861dd4bf2b3f0f47e6051d1a8"),
    "cookie_secret": os.environ.get("COOKIE_SECRET", "fwqVGC0JHS-CTBy5UeEGA8CG7xtoi9wqPqHBtaZVfQU="),
    "redirect_url": os.environ.get("REDIRECT_URL", "https://ai.mais.agency/oauth2/callback"),
    "auth_url": "https://oauth.yandex.ru/authorize",
    "token_url": "https://oauth.yandex.ru/token",
    "userinfo_url": "https://login.yandex.ru/info",
    "listen": os.environ.get("LISTEN", "127.0.0.1:4180"),
    "domain": os.environ.get("COOKIE_DOMAIN", ".mais.agency"),
    "allowed_emails_file": "/etc/oauth2-proxy/authenticated_emails.txt",
    "cookie_name": "_yandex_auth",
    "cookie_ttl": 7 * 24 * 3600,
}

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
log = logging.getLogger("yandex-auth")

CTX = ssl.create_default_context()


def _sign(data: bytes) -> str:
    key = CONFIG["cookie_secret"].encode()
    sig = hmac.new(key, data, hashlib.sha256).digest()
    return base64.urlsafe_b64encode(sig).rstrip(b"=").decode()


def make_cookie(user_email: str) -> str:
    payload = f"{user_email}|{int(time.time())}"
    payload_b64 = base64.urlsafe_b64encode(payload.encode()).rstrip(b"=").decode()
    sig = _sign(payload_b64.encode())
    return f"{payload_b64}.{sig}"


def verify_cookie(value: str) -> str | None:
    try:
        payload_b64, sig = value.rsplit(".", 1)
        expected = _sign(payload_b64.encode())
        if not hmac.compare_digest(sig, expected):
            return None
        payload = base64.urlsafe_b64decode(payload_b64 + "==").decode()
        email, ts = payload.rsplit("|", 1)
        if time.time() - float(ts) > CONFIG["cookie_ttl"]:
            return None
        return email
    except Exception:
        return None


def is_email_allowed(email: str) -> bool:
    try:
        with open(CONFIG["allowed_emails_file"]) as f:
            allowed = [line.strip() for line in f if line.strip() and not line.startswith("#")]
        return email in allowed
    except FileNotFoundError:
        return True


def yandex_request(url: str, data: dict | None = None, headers: dict | None = None) -> dict:
    body = urllib.parse.urlencode(data).encode() if data else None
    req = urllib.request.Request(url, data=body, headers=headers or {})
    with urllib.request.urlopen(req, context=CTX) as resp:
        return json.loads(resp.read())


class AuthHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        log.info(fmt % args)

    def _set_cookie(self, name: str, value: str, path: str = "/"):
        parts = [f"{name}={value}", f"Path={path}", f"Domain={CONFIG['domain']}", "Max-Age={}".format(CONFIG["cookie_ttl"]), "HttpOnly", "Secure", "SameSite=Lax"]
        self.send_header("Set-Cookie", "; ".join(parts))

    def _redirect(self, url: str):
        self.send_response(302)
        self.send_header("Location", url)
        self.end_headers()

    def _text(self, code: int, body: str, content_type: str = "text/plain"):
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.end_headers()
        self.wfile.write(body.encode())

    def _get_cookie(self, name: str) -> str | None:
        cookies = self.headers.get("Cookie", "")
        for part in cookies.split(";"):
            k, _, v = part.strip().partition("=")
            if k == name:
                return v
        return None

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        qs = urllib.parse.parse_qs(parsed.query)

        if path == "/auth":
            self.handle_auth()
        elif path == "/start":
            self.handle_start(qs)
        elif path in ("/callback", "/oauth2/callback"):
            self.handle_callback(qs)
        elif path == "/ping":
            self._text(200, "OK")
        else:
            self._text(404, "Not Found")

    def handle_auth(self):
        cookie = self._get_cookie(CONFIG["cookie_name"])
        if cookie:
            email = verify_cookie(cookie)
            if email and is_email_allowed(email):
                self.send_response(200)
                self.send_header("X-Auth-Request-User", email.split("@")[0])
                self.send_header("X-Auth-Request-Email", email)
                self.end_headers()
                return
        self.send_response(401)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"unauthorized")

    def handle_start(self, qs):
        rd = qs.get("rd", ["/"])[0]
        state = base64.urlsafe_b64encode(os.urandom(32)).rstrip(b"=").decode()
        params = urllib.parse.urlencode({
            "response_type": "code",
            "client_id": CONFIG["client_id"],
            "redirect_uri": CONFIG["redirect_url"],
            "state": f"{state}:{rd}",
            "scope": "login:info login:email",
        })
        self._redirect(f"{CONFIG['auth_url']}?{params}")

    def handle_callback(self, qs):
        if "error" in qs:
            error = qs["error"][0]
            desc = qs.get("error_description", ["unknown"])[0]
            self._text(403, f"Login Failed: {error} - {desc}")
            return

        code = qs.get("code", [None])[0]
        state_val = qs.get("state", [""])[0]
        if not code:
            self._text(400, "Missing code parameter")
            return

        state_parts = state_val.split(":", 1)
        rd = state_parts[1] if len(state_parts) > 1 else "/"

        token_data = yandex_request(CONFIG["token_url"], data={
            "grant_type": "authorization_code",
            "code": code,
            "client_id": CONFIG["client_id"],
            "client_secret": CONFIG["client_secret"],
        })

        access_token = token_data.get("access_token")
        if not access_token:
            self._text(500, "Failed to get access token")
            return

        userinfo = yandex_request(CONFIG["userinfo_url"], headers={
            "Authorization": f"OAuth {access_token}",
        })

        email = userinfo.get("default_email")
        if not email:
            emails = userinfo.get("emails", [])
            if isinstance(emails, list) and emails:
                email = emails[0]
        if not email:
            self._text(500, "Could not determine user email")
            return

        if not is_email_allowed(email):
            self._text(403, f"Email {email} is not authorized")
            return

        cookie_val = make_cookie(email)
        self.send_response(302)
        self._set_cookie(CONFIG["cookie_name"], cookie_val)
        self.send_header("Location", rd)
        self.end_headers()


def run():
    host, port = CONFIG["listen"].split(":")
    server = http.server.HTTPServer((host, int(port)), AuthHandler)
    log.info(f"Starting yandex-auth on {CONFIG['listen']}")
    server.serve_forever()


if __name__ == "__main__":
    run()
