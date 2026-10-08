from pathlib import Path
import yaml

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.yaml"

DEFAULTS = {
    "router_ip": "",
    "expected_authentication": "WPA2-Personal",
    "expected_cipher": "CCMP",
    "connect_timeout": 20,
    "max_connect_time": 15,
    "connect_attempts": 5,
}

def load_config():
    """Load config.yaml from the project root, filling in defaults."""
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(
            "config.yaml not found. Copy config.example.yaml to config.yaml and edit it.")
    with open(CONFIG_PATH) as f:
        cfg = yaml.safe_load(f) or {}
    for key, value in DEFAULTS.items():
        cfg.setdefault(key, value)
    for required in ("target_ssid", "target_profile"):
        if not cfg.get(required):
            raise ValueError(f"'{required}' is missing in config.yaml")
    return cfg
