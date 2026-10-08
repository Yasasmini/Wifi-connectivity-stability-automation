"""STAGES 6-8 - DHCP address, gateway, DNS and internet (a connection that really works)."""
import pytest
from core import wifi_manager as wm


def test_TC03_1_dhcp_assigns_valid_address(connected_wifi):
    """Client got a real DHCP address (not 169.254.x.x, which means DHCP failed)."""
    ip = wm.get_ip_config()["ipv4"]
    print("\nIPv4:", ip)
    assert wm.has_valid_ip(ip), f"No valid address (got {ip})"


def test_TC03_2_dhcp_server_present(connected_wifi):
    """Address came from DHCP and the DHCP server is identified."""
    c = wm.get_ip_config()
    print("\nDHCP:", c["dhcp_enabled"], c["dhcp_server"])
    assert c["dhcp_enabled"], "DHCP is not enabled on the adapter"
    assert c["dhcp_server"], "No DHCP server reported"


def test_TC03_3_gateway_assigned(cfg, connected_wifi):
    """Default gateway is set (and equals router_ip from config, if given)."""
    gw = wm.get_ip_config()["gateway"]
    print("\nGateway:", gw)
    assert gw, "No default gateway"
    if cfg.get("router_ip"):
        assert gw == cfg["router_ip"], f"Gateway {gw} != configured router_ip {cfg['router_ip']}"


def test_TC03_4_gateway_reachable(connected_wifi):
    """Router answers ping: the local IP path works."""
    gw = wm.get_ip_config()["gateway"]
    assert wm.ping_ok(gw), f"Cannot ping gateway {gw}"


def test_TC03_5_dns_resolves(connected_wifi):
    """Names can be resolved."""
    assert wm.dns_ok("google.com"), "DNS lookup failed"


def test_TC03_6_internet_reachable(connected_wifi):
    """Public address answers ping: traffic goes through the router to the internet."""
    assert wm.ping_ok("8.8.8.8"), "Cannot reach 8.8.8.8"


def test_TC03_7_dhcp_renew(connected_wifi):
    """Release and renew the lease; a valid address must come back (needs Administrator)."""
    if not wm.is_admin():
        pytest.skip("Run the terminal as Administrator for ipconfig /release and /renew")
    assert wm.renew_dhcp(), "No valid address after DHCP renew"
