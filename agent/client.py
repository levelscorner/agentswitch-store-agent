"""Minimal MCP client for the AgentSwitch Website seat.

login -> Bearer token -> tools/call. The Bearer path needs no CSRF header.
Handles the documented trap: a JSON-RPC error still returns HTTP 200, with the
failure inside the envelope. The token is held in memory only and never printed.

Zero dependencies (standard-library urllib). Run a smoke test with:

    set -a; source .env; set +a
    python3 -m agent.client
"""
import json
import os
import ssl
import urllib.error
import urllib.request

from . import config


def _ssl_context():
    """python.org Python on macOS can't find the system root certs; use certifi's bundle."""
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        try:
            return ssl.create_default_context()
        except Exception:
            return None


_SSL = _ssl_context()


class MCPError(Exception):
    """A JSON-RPC error returned by the platform (arrives inside an HTTP-200 body)."""

    def __init__(self, code, message):
        super().__init__(f"[{code}] {message}")
        self.code = code
        self.message = message


def _http(method, url, token=None, body=None, timeout=30):
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Accept": "application/json"}
    if data is not None:
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = "Bearer " + token
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=_SSL) as r:
            return r.status, _decode(r.read())
    except urllib.error.HTTPError as e:
        return e.code, _decode(e.read() if e.fp else b"")


def _decode(raw):
    """Return parsed JSON when the body is JSON, else the raw text. The website
    render/serve endpoints answer HTML/CSS, not JSON, so blind json.loads crashed."""
    if not raw:
        return None
    try:
        return json.loads(raw.decode())
    except Exception:
        try:
            return raw.decode("utf-8", "replace")
        except Exception:
            return raw


class Client:
    def __init__(self, base=None, token=None):
        self.base = (base or config.AS_BASE).rstrip("/")
        self._token = token

    @classmethod
    def login(cls, base=None, email=None, password=None):
        base = (base or config.AS_BASE).rstrip("/")
        email = email or config.AS_EMAIL
        password = password or os.environ.get("AS_PASSWORD")
        if not password:
            raise SystemExit("Set AS_PASSWORD in the environment (see .env.example).")
        status, body = _http("POST", base + "/api/auth/login",
                             body={"email": email, "password": password})
        if status != 200 or not isinstance(body, dict) or not body.get("token"):
            raise SystemExit(f"Login failed (HTTP {status}). Check AS_BASE / email / password.")
        return cls(base, body["token"])

    def me(self):
        _, body = _http("GET", self.base + "/api/auth/me", token=self._token)
        return body or {}

    def rpc(self, method, params):
        """One JSON-RPC call. Raises MCPError when the envelope carries an error."""
        _, body = _http("POST", self.base + "/api/mcp", token=self._token,
                        body={"jsonrpc": "2.0", "id": 1, "method": method, "params": params})
        if isinstance(body, dict) and body.get("error"):
            e = body["error"]
            raise MCPError(e.get("code"), e.get("message"))
        return body.get("result") if isinstance(body, dict) else None

    def list_tools(self):
        return (self.rpc("tools/list", {}) or {}).get("tools", [])

    def call(self, name, arguments=None):
        """Call one tool; unwrap the MCP text-content into a Python object."""
        res = self.rpc("tools/call", {"name": name, "arguments": arguments or {}})
        content = (res or {}).get("content")
        if isinstance(content, list):
            text = "".join(c.get("text", "") for c in content)
            if res.get("isError"):
                raise MCPError("tool_error", text[:300])
            try:
                return json.loads(text)
            except Exception:
                return text
        return res


def _smoke():
    c = Client.login()
    me = c.me()
    tools = c.list_tools()
    print(f"seat:         {me.get('email')}  ({me.get('name')})")
    print(f"roles:        {me.get('roles')}")
    print(f"allowed_apps: {me.get('allowed_apps')}")
    print(f"MCP tools visible to our seat: {len(tools)}")


if __name__ == "__main__":
    _smoke()
