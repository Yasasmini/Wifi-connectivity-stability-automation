"""Negative tests - real failures the device must handle.

They use SEPARATE test profiles, so your real saved profile is never changed.
"""
from core import wifi_manager as wm

TEST_PROFILE = "AUTOTEST_TEMP_PROFILE"


def _restore(cfg):
    """Delete the temp profile and put the laptop back on the real network."""
    wm.delete_profile(TEST_PROFILE)
    wm.connect_wifi(cfg["target_profile"])


def test_TC04_1_nonexistent_profile_rejected():
    """Windows refuses a profile that does not exist."""
    assert wm.connect_wifi("AUTOMATION_NO_SUCH_PROFILE_12345") is False


def test_TC04_2_wrong_password_fails_handshake(cfg):
    """Wrong passphrase -> 4-way handshake fails -> link never reaches 'connected'."""
    try:
        wm.disconnect_wifi()
        assert wm.create_test_profile(TEST_PROFILE, cfg["target_ssid"], "wrong-password-123")
        wm.connect_wifi(TEST_PROFILE, cfg["target_ssid"])
        assert wm.wait_for_connection(cfg["target_ssid"], timeout=15) is None, \
            "Connected with a wrong password!"
    finally:
        _restore(cfg)


def test_TC04_3_network_not_in_range_fails(cfg):
    """Profile for an SSID that is not on the air never connects."""
    fake_ssid = "AUTOTEST_NOT_IN_RANGE"
    try:
        wm.disconnect_wifi()
        assert wm.create_test_profile(TEST_PROFILE, fake_ssid, "whatever-password-1")
        wm.connect_wifi(TEST_PROFILE, fake_ssid)
        assert wm.wait_for_connection(fake_ssid, timeout=10) is None
    finally:
        _restore(cfg)
