"""STAGE 1 - Beacon / scan: the AP announces itself; the client sees its settings."""
from core import wifi_manager as wm


def test_TC01_1_scan_discovers_networks():
    """Adapter receives beacons/probe responses and lists nearby networks."""
    ssids = wm.get_available_ssids()
    print("\nDiscovered:", ssids)
    assert ssids, "No networks discovered - is Wi-Fi on?"


def test_TC01_2_target_beacon_visible(cfg):
    """Our router's beacon is received and its SSID is in the scan results."""
    info = wm.get_beacon_info(cfg["target_ssid"])
    print("\nBeacon info:", info)
    assert info is not None, f"'{cfg['target_ssid']}' not seen in scan"


def test_TC01_3_beacon_reports_radio_details(cfg):
    """Beacon carries radio details: BSSID, signal, radio type, band, channel."""
    info = wm.get_beacon_info(cfg["target_ssid"])
    assert info is not None, "Target not found in scan"
    for field in ("bssid", "radio", "band", "channel"):
        assert info[field], f"Beacon info missing '{field}'"
    assert info["signal_pct"] > 0, "Signal reported as 0%"


def test_TC01_4_beacon_advertises_expected_security(cfg):
    """Router advertises the security mode we configured (e.g. WPA2-Personal / CCMP)."""
    info = wm.get_beacon_info(cfg["target_ssid"])
    assert info is not None, "Target not found in scan"
    assert info["authentication"] == cfg["expected_authentication"]
    assert info["encryption"] == cfg["expected_cipher"]
