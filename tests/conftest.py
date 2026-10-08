import os
import sys
import time
from pathlib import Path

import pytest

from core import wifi_manager as wm
from core.config_reader import load_config
from core.logger import get_logger

log = get_logger("conftest")
ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="session")
def cfg():
    return load_config()


@pytest.fixture
def connected_wifi(cfg):
    """Precondition: laptop is connected to the target SSID and has a valid DHCP IP.

    Tests that need a working link use this, so each one runs correctly on its own.
    """
    ssid = cfg["target_ssid"]
    if not (wm.get_state() == "connected" and wm.get_connected_ssid() == ssid):
        wm.disconnect_wifi()
        wm.connect_wifi(cfg["target_profile"])
        assert wm.wait_for_connection(ssid, cfg["connect_timeout"]) is not None, \
            "Precondition failed: link did not come up"
    assert wm.wait_for_ip(cfg["connect_timeout"]) is not None, \
        "Precondition failed: no valid DHCP address"
    yield


def pytest_collection_modifyitems(config, items):
    """Mark tests by folder, and skip hardware tests when not on Windows."""
    for item in items:
        parts = Path(str(item.fspath)).parts
        if "hardware" in parts:
            item.add_marker(pytest.mark.hardware)
            if sys.platform != "win32":
                item.add_marker(pytest.mark.skip(reason="hardware tests need Windows (netsh)"))
        elif "unit" in parts:
            item.add_marker(pytest.mark.unit)


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """On a failing hardware test, save the evidence (link + IP state) to logs/."""
    outcome = yield
    rep = outcome.get_result()
    if rep.when == "call" and rep.failed and item.get_closest_marker("hardware"):
        logs = ROOT / "logs"
        logs.mkdir(exist_ok=True)
        stamp = time.strftime("%Y%m%d_%H%M%S")
        with open(logs / f"{item.name}_{stamp}.txt", "w") as f:
            f.write("=== netsh wlan show interfaces ===\n")
            f.write(wm.run_command("netsh wlan show interfaces").stdout)
            f.write("\n=== ipconfig /all ===\n")
            f.write(wm.run_command("ipconfig /all").stdout)
            f.write("\n=== netsh wlan show networks mode=bssid ===\n")
            f.write(wm.run_command("netsh wlan show networks mode=bssid").stdout)
