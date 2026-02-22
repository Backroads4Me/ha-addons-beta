"""LibreCoach Settings Server — lightweight HTTP server for the ingress sidebar UI.

Serves static files and provides a REST API for reading/writing settings.
Runs as an s6-overlay longrun service on port 8099 (ingress_port).
"""

import json
import logging
import os
import urllib.request
import urllib.error
from functools import partial
from http.server import HTTPServer, SimpleHTTPRequestHandler

log = logging.getLogger("settings_server")

SETTINGS_PATH = "/data/librecoach-settings.json"
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
LISTEN_PORT = 8099
SUPERVISOR_URL = "http://supervisor/core/api"

# Only accept connections from HA ingress proxy and localhost (for host_network)
ALLOWED_IPS = {"172.30.32.2", "127.0.0.1"}

DEFAULTS = {
    "geo_enabled": False,
    "geo_device_tracker_primary": "",
    "geo_device_tracker_secondary": "",
    "geo_update_threshold": 10,
    "victron_enabled": True,
    "microair_enabled": False,
    "microair_email": "",
    "microair_password": "",
    "ble_scan_interval": 30,
    "beta_enabled": False,
}


def _read_settings():
    """Read settings from disk, merging with defaults."""
    settings = dict(DEFAULTS)
    if os.path.exists(SETTINGS_PATH):
        try:
            with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
                settings.update(json.load(f))
        except (json.JSONDecodeError, OSError) as exc:
            log.warning("Failed to read settings: %s", exc)
    return settings


def _write_settings(data):
    """Write settings to disk."""
    # Only accept known keys and enforce default types
    settings = {}
    for key, default_val in DEFAULTS.items():
        if key in data:
            val = data[key]
            exp_type = type(default_val)
            if exp_type is int:
                try:
                    val = int(val)
                except (ValueError, TypeError):
                    val = default_val
            elif exp_type is bool:
                if isinstance(val, str):
                    val = val.lower() == "true"
                else:
                    val = bool(val)
            elif exp_type is float:
                try:
                    val = float(val)
                except (ValueError, TypeError):
                    val = default_val
            elif exp_type is str:
                val = str(val) if val is not None else ""
            else:
                val = default_val
            settings[key] = val
        else:
            settings[key] = default_val
    with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=2)
    return settings


def _fetch_entities(domain=None):
    """Fetch entity list from Supervisor API, optionally filtered by domain."""
    token = os.environ.get("SUPERVISOR_TOKEN", "")
    if not token:
        return []
    url = f"{SUPERVISOR_URL}/states"
    req = urllib.request.Request(url, method="GET")
    req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            states = json.loads(resp.read().decode("utf-8"))
    except Exception as exc:
        log.warning("Failed to fetch entities: %s", exc)
        return []

    entities = []
    for entity in states:
        eid = entity.get("entity_id", "")
        if domain and not eid.startswith(f"{domain}."):
            continue
        entities.append({
            "entity_id": eid,
            "friendly_name": entity.get("attributes", {}).get("friendly_name", eid),
        })
    entities.sort(key=lambda e: e["entity_id"])
    return entities


class SettingsHandler(SimpleHTTPRequestHandler):
    """Handle API requests and serve static files."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=STATIC_DIR, **kwargs)

    def log_message(self, format, *args):
        log.debug(format, *args)

    def _check_ip(self):
        """Verify request comes from HA ingress proxy."""
        client_ip = self.client_address[0]
        if client_ip not in ALLOWED_IPS:
            log.warning("Rejected connection from %s", client_ip)
            self.send_error(403, "Forbidden")
            return False
        return True

    def _send_json(self, data, status=200):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if not self._check_ip():
            return

        if self.path == "/api/settings" or self.path == "./api/settings":
            self._send_json(_read_settings())
            return

        if self.path.startswith("/api/entities"):
            # Parse ?domain=device_tracker
            domain = None
            if "?" in self.path:
                params = self.path.split("?", 1)[1]
                for param in params.split("&"):
                    if param.startswith("domain="):
                        domain = param.split("=", 1)[1]
            self._send_json(_fetch_entities(domain))
            return

        # Serve static files
        super().do_GET()

    def do_POST(self):
        if not self._check_ip():
            return

        if self.path == "/api/settings" or self.path == "./api/settings":
            content_length = int(self.headers.get("Content-Length", 0))
            if content_length == 0:
                self._send_json({"error": "Empty body"}, 400)
                return
            try:
                body = self.rfile.read(content_length)
                data = json.loads(body.decode("utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError) as exc:
                self._send_json({"error": str(exc)}, 400)
                return

            saved = _write_settings(data)
            log.info("Settings updated")
            self._send_json({"ok": True, "settings": saved})
            return

        self.send_error(404)


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s: %(message)s",
    )

    server = HTTPServer(("0.0.0.0", LISTEN_PORT), SettingsHandler)
    log.info("Settings server listening on port %d", LISTEN_PORT)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
