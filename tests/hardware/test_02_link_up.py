"""STAGES 3-5 - Authentication, association and 4-way handshake (the Wi-Fi link comes up)."""
from core import wifi_manager as wm


def test_TC02_1_connect_valid_profile(cfg):
    """Connect with the saved profile; link must reach 'connected' on the right SSID."""
    wm.disconnect_wifi()
    assert wm.connect_wifi(cfg["target_profile"]), "Connect request was rejected"
    t = wm.wait_for_connection(cfg["target_ssid"], cfg["connect_timeout"])
    print(f"\nLink up in {t}s")
    assert t is not None, "Request accepted but link never came up"


def test_TC02_2_link_uses_expected_security(cfg, connected_wifi):
    """Negotiated authentication and cipher match what the router should use."""
    info = wm.get_interface_info()
    print("\nAuth:", info.get("Authentication"), "| Cipher:", info.get("Cipher"))
    assert info.get("Authentication") == cfg["expected_authentication"]
    assert info.get("Cipher") == cfg["expected_cipher"]


def test_TC02_3_link_details_reported(cfg, connected_wifi):
    """Link reports radio type, band, channel, signal and data rates."""
    info = wm.get_interface_info()
    print("\nLink:", {k: info.get(k) for k in
          ("Radio type", "Band", "Channel", "Signal", "Receive rate (Mbps)", "Transmit rate (Mbps)")})
    for field in ("Radio type", "Band", "Channel", "Signal", "Receive rate (Mbps)", "Transmit rate (Mbps)"):
        assert info.get(field), f"Missing '{field}' in interface info"
