"""Stability - measured connection time and repeated reconnects."""
import pytest
from core import wifi_manager as wm


def test_TC05_1_connection_time(cfg):
    """Measure connect time over several attempts; slowest must stay under the limit."""
    times = []
    for _ in range(cfg["connect_attempts"]):
        wm.disconnect_wifi()
        wm.connect_wifi(cfg["target_profile"])
        t = wm.wait_for_connection(cfg["target_ssid"], cfg["connect_timeout"])
        assert t is not None, "A connection attempt failed"
        times.append(t)
    avg, worst = sum(times) / len(times), max(times)
    print(f"\nconnect time: avg={avg:.2f}s  max={worst:.2f}s  runs={times}")
    assert worst <= cfg["max_connect_time"], f"Slowest connect {worst}s > {cfg['max_connect_time']}s"


@pytest.mark.stress
@pytest.mark.parametrize("cycle", range(1, 11))
def test_TC05_2_reconnect_cycle(cfg, cycle):
    """Disconnect and reconnect; the link AND a valid IP must come back every time."""
    wm.disconnect_wifi()
    wm.connect_wifi(cfg["target_profile"])
    assert wm.wait_for_connection(cfg["target_ssid"], cfg["connect_timeout"]) is not None, \
        f"Cycle {cycle}: link did not come up"
    assert wm.wait_for_ip(cfg["connect_timeout"]) is not None, \
        f"Cycle {cycle}: link up but no valid IP"
