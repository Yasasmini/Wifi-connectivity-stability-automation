"""Unit tests: do the parsers read netsh/ipconfig text correctly? (no hardware needed)

These use SAMPLE Windows output, and mocks for failure cases that are hard to create on a real device.
"""
from unittest.mock import patch, MagicMock

from core import wifi_manager as wm

INTERFACE = """
    Name                   : Wi-Fi
    State                  : connected
    SSID                   : HomeNet
    BSSID                  : aa:bb:cc:dd:ee:ff
    Network type           : Infrastructure
    Radio type             : 802.11ac
    Authentication         : WPA2-Personal
    Cipher                 : CCMP
    Band                   : 5 GHz
    Channel                : 36
    Receive rate (Mbps)    : 866.7
    Transmit rate (Mbps)   : 866.7
    Signal                 : 99%
"""

NETWORKS = """
Interface name : Wi-Fi
There are 2 networks currently visible.

SSID 1 : HomeNet
    Network type            : Infrastructure
    Authentication          : WPA2-Personal
    Encryption              : CCMP
    BSSID 1                 : aa:bb:cc:dd:ee:ff
         Signal             : 80%
         Radio type         : 802.11ac
         Band               : 5 GHz
         Channel            : 36
    BSSID 2                 : aa:bb:cc:dd:ee:00
         Signal             : 91%
         Radio type         : 802.11n
         Band               : 2.4 GHz
         Channel            : 6

SSID 2 : Neighbour
    Network type            : Infrastructure
    Authentication          : WPA3-Personal
    Encryption              : CCMP
    BSSID 1                 : 11:22:33:44:55:66
         Signal             : 40%
         Radio type         : 802.11ax
         Band               : 5 GHz
         Channel            : 149
"""

IPCONFIG = """
Windows IP Configuration

Ethernet adapter Ethernet:

   Media State . . . . . . . . . . . : Media disconnected

Wireless LAN adapter Wi-Fi:

   Connection-specific DNS Suffix  . : lan
   IPv6 Address. . . . . . . . . . . : 2001:db8::1234
   IPv4 Address. . . . . . . . . . . : 192.168.1.45(Preferred)
   Subnet Mask . . . . . . . . . . . : 255.255.255.0
   Default Gateway . . . . . . . . . : fe80::1%12
                                       192.168.1.1
   DHCP Enabled. . . . . . . . . . . : Yes
   DHCP Server . . . . . . . . . . . : 192.168.1.1
"""


def test_parse_interface_connected():
    f = wm.parse_fields(INTERFACE)
    assert f["State"] == "connected"
    assert f["SSID"] == "HomeNet"          # must not be confused with BSSID
    assert f["BSSID"] == "aa:bb:cc:dd:ee:ff"
    assert f["Authentication"] == "WPA2-Personal" and f["Cipher"] == "CCMP"


def test_parse_interface_detects_other_ssid():
    f = wm.parse_fields(INTERFACE.replace("HomeNet", "Wrong_Test_Network"))
    assert f["SSID"] == "Wrong_Test_Network"      # parser reads whatever is connected


def test_parse_interface_reads_tkip_cipher():
    f = wm.parse_fields(INTERFACE.replace("CCMP", "TKIP"))
    assert f["Cipher"] == "TKIP"


def test_parse_networks_beacon_details():
    nets = wm.parse_networks(NETWORKS)
    assert [n["ssid"] for n in nets] == ["HomeNet", "Neighbour"]
    home = nets[0]
    assert home["authentication"] == "WPA2-Personal" and home["encryption"] == "CCMP"
    assert len(home["aps"]) == 2
    assert home["aps"][0]["channel"] == "36" and home["aps"][1]["band"] == "2.4 GHz"
    assert nets[1]["authentication"] == "WPA3-Personal"


@patch("core.wifi_manager.run_command")
def test_beacon_info_picks_strongest_ap(mock_run):
    mock_run.return_value = MagicMock(returncode=0, stdout=NETWORKS, stderr="")
    info = wm.get_beacon_info("HomeNet")
    assert info["bssid"] == "aa:bb:cc:dd:ee:00" and info["signal_pct"] == 91
    assert wm.get_beacon_info("NotThere") is None


@patch("core.wifi_manager.run_command")
def test_scan_failure_returns_empty_list(mock_run):
    mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="Wi-Fi scan failed")
    assert wm.get_available_ssids() == []


def test_parse_ipconfig_dhcp_gateway():
    c = wm.parse_ipconfig(IPCONFIG, "Wi-Fi")
    assert c["ipv4"] == "192.168.1.45"
    assert c["gateway"] == "192.168.1.1"          # IPv4 on the continuation line, after the IPv6 one
    assert c["dhcp_enabled"] is True and c["dhcp_server"] == "192.168.1.1"


def test_parse_ipconfig_ignores_other_adapters():
    c = wm.parse_ipconfig(IPCONFIG, "Ethernet")
    assert c["ipv4"] is None


def test_apipa_means_dhcp_failed():
    assert wm.is_apipa("169.254.10.5") is True
    assert wm.has_valid_ip("169.254.10.5") is False
    assert wm.has_valid_ip("192.168.1.45") is True
    assert wm.has_valid_ip(None) is False


@patch("core.wifi_manager.get_interface_info")
@patch("core.wifi_manager.time.sleep")
def test_wait_for_connection_times_out(mock_sleep, mock_info):
    mock_info.return_value = {"State": "disconnected"}
    assert wm.wait_for_connection("HomeNet", timeout=0.05) is None


@patch("core.wifi_manager.get_interface_info")
def test_wait_for_connection_success(mock_info):
    mock_info.return_value = {"State": "connected", "SSID": "HomeNet"}
    assert wm.wait_for_connection("HomeNet", timeout=5) is not None
