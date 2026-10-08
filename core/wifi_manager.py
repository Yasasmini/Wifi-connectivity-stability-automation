"""Helpers that drive the Windows Wi-Fi client with netsh/ipconfig/ping/nslookup.

Layout: small functions that RUN a command, and pure parse_* functions that turn
the text into data. The parse_* functions are unit-tested with sample output.
"""
import os
import re
import subprocess
import tempfile
import time
from xml.sax.saxutils import escape

from core.logger import get_logger

log = get_logger(__name__)


# ---------------------------------------------------------------- running commands
def run_command(cmd, timeout=30):
    """Run a shell command and return the CompletedProcess (stdout, stderr, returncode)."""
    return subprocess.run(cmd, capture_output=True, text=True, shell=True, timeout=timeout)


# ---------------------------------------------------------------- generic parsing
def parse_fields(text):
    """Turn 'Key  : Value' lines into a dict (first occurrence of each key wins)."""
    fields = {}
    for line in text.splitlines():
        m = re.match(r"^\s*([^:]+?)\s*:\s*(.*?)\s*$", line)
        if m:
            key = re.sub(r"[ .]+$", "", m.group(1))     # 'IPv4 Address. . . .' -> 'IPv4 Address'
            fields.setdefault(key, m.group(2))
    return fields


# ---------------------------------------------------------------- STAGE 1: beacon / scan
def parse_networks(text):
    """Parse 'netsh wlan show networks mode=bssid' into a list of networks.

    Each network: ssid, authentication, encryption and aps (one entry per BSSID,
    with signal, radio type, band, channel) = what the AP advertises in its beacons.
    """
    networks = []
    parts = re.split(r"^SSID \d+ : ?", text, flags=re.MULTILINE)
    for part in parts[1:]:
        lines = part.splitlines()
        ssid = lines[0].strip() if lines else ""
        body = "\n".join(lines[1:])
        bssid_parts = re.split(r"^\s*BSSID \d+\s*:\s*", body, flags=re.MULTILINE)
        net = parse_fields(bssid_parts[0])
        aps = []
        for bp in bssid_parts[1:]:
            bl = bp.splitlines()
            f = parse_fields("\n".join(bl[1:]))
            aps.append({
                "bssid": bl[0].strip(),
                "signal": f.get("Signal"),
                "radio": f.get("Radio type"),
                "band": f.get("Band"),
                "channel": f.get("Channel"),
            })
        networks.append({
            "ssid": ssid,
            "authentication": net.get("Authentication"),
            "encryption": net.get("Encryption"),
            "aps": aps,
        })
    return networks


def get_networks():
    result = run_command("netsh wlan show networks mode=bssid")
    if result.returncode != 0:
        log.error("Scan failed: %s", result.stderr.strip())
        return []
    return parse_networks(result.stdout)


def get_available_ssids():
    return [n["ssid"] for n in get_networks() if n["ssid"]]


def get_beacon_info(ssid):
    """What the target AP advertises: security, strongest BSSID, radio, band, channel, signal."""
    for net in get_networks():
        if net["ssid"] == ssid:
            aps = sorted(net["aps"], key=lambda a: int((a["signal"] or "0%").rstrip("%") or 0), reverse=True)
            ap = aps[0] if aps else {}
            return {
                "ssid": ssid,
                "authentication": net["authentication"],
                "encryption": net["encryption"],
                "bssid": ap.get("bssid"),
                "signal_pct": int((ap.get("signal") or "0%").rstrip("%") or 0),
                "radio": ap.get("radio"),
                "band": ap.get("band"),
                "channel": ap.get("channel"),
            }
    return None


# ---------------------------------------------------------------- STAGES 3-5: link (auth, assoc, 4-way handshake)
def get_interface_info():
    """Current connection details from 'netsh wlan show interfaces' as a dict."""
    return parse_fields(run_command("netsh wlan show interfaces").stdout)


def get_state():
    return get_interface_info().get("State")


def get_connected_ssid():
    return get_interface_info().get("SSID")


def connect_wifi(profile, ssid=None):
    """Ask Windows to connect. True only means the request was accepted."""
    cmd = f'netsh wlan connect name="{profile}"'
    if ssid:
        cmd += f' ssid="{ssid}"'
    return run_command(cmd).returncode == 0


def disconnect_wifi():
    run_command("netsh wlan disconnect")
    time.sleep(1)


def wait_for_connection(ssid, timeout=20):
    """Wait until the link is up on `ssid`. Returns seconds taken, or None on timeout."""
    start = time.time()
    while time.time() - start < timeout:
        info = get_interface_info()
        if info.get("State") == "connected" and info.get("SSID") == ssid:
            return round(time.time() - start, 2)
        time.sleep(0.5)
    return None


def create_test_profile(profile_name, ssid, password, auth="WPA2PSK", encryption="AES"):
    """Create a separate profile (never touches your real one). Use auth='WPA3SAE' for WPA3."""
    xml = f"""<?xml version="1.0"?>
<WLANProfile xmlns="http://www.microsoft.com/networking/WLAN/profile/v1">
  <name>{escape(profile_name)}</name>
  <SSIDConfig><SSID><name>{escape(ssid)}</name></SSID></SSIDConfig>
  <connectionType>ESS</connectionType>
  <connectionMode>manual</connectionMode>
  <MSM><security>
    <authEncryption>
      <authentication>{auth}</authentication>
      <encryption>{encryption}</encryption>
      <useOneX>false</useOneX>
    </authEncryption>
    <sharedKey>
      <keyType>passPhrase</keyType>
      <protected>false</protected>
      <keyMaterial>{escape(password)}</keyMaterial>
    </sharedKey>
  </security></MSM>
</WLANProfile>"""
    path = os.path.join(tempfile.gettempdir(), f"{profile_name}.xml")
    with open(path, "w") as f:
        f.write(xml)
    try:
        return run_command(f'netsh wlan add profile filename="{path}"').returncode == 0
    finally:
        os.remove(path)


def delete_profile(profile_name):
    run_command(f'netsh wlan delete profile name="{profile_name}"')


# ---------------------------------------------------------------- STAGES 6-8: DHCP, gateway, DNS, internet
def _adapter_section(text, adapter):
    """Lines of the ipconfig section whose header ends with the adapter name."""
    section, inside = [], False
    for line in text.splitlines():
        if line and not line[0].isspace() and line.rstrip().endswith(":"):
            inside = line.rstrip().rstrip(":").endswith(adapter)
            continue
        if inside:
            section.append(line)
    return section


def parse_ipconfig(text, adapter="Wi-Fi"):
    """Parse 'ipconfig /all' for one adapter: ipv4, subnet, gateway, dhcp_enabled, dhcp_server."""
    lines = _adapter_section(text, adapter)
    fields = parse_fields("\n".join(lines))

    def first_ipv4(value):
        m = re.search(r"\d{1,3}(?:\.\d{1,3}){3}", value or "")
        return m.group(0) if m else None

    gateway = None                       # the first line may be IPv6; IPv4 can be on the next line
    for i, line in enumerate(lines):
        if line.strip().startswith("Default Gateway"):
            chunk = [line.split(":", 1)[1] if ":" in line else ""]
            for nxt in lines[i + 1:]:
                if not nxt.strip() or re.search(r"\s:(\s|$)", nxt):
                    break
                chunk.append(nxt)
            gateway = first_ipv4(" ".join(chunk))
            break

    return {
        "ipv4": first_ipv4(fields.get("IPv4 Address")),
        "subnet": first_ipv4(fields.get("Subnet Mask")),
        "gateway": gateway,
        "dhcp_enabled": (fields.get("DHCP Enabled") or "").lower() == "yes",
        "dhcp_server": first_ipv4(fields.get("DHCP Server")),
    }


def get_ip_config():
    adapter = get_interface_info().get("Name", "Wi-Fi")
    return parse_ipconfig(run_command("ipconfig /all").stdout, adapter)


def is_apipa(ip):
    """169.254.x.x = Windows gave itself an address because DHCP failed."""
    return bool(ip) and ip.startswith("169.254.")


def has_valid_ip(ip):
    return bool(ip) and not is_apipa(ip) and ip != "0.0.0.0"


def wait_for_ip(timeout=20):
    """Wait for a valid DHCP address. Returns the ip config dict, or None on timeout."""
    start = time.time()
    while time.time() - start < timeout:
        cfg = get_ip_config()
        if has_valid_ip(cfg["ipv4"]):
            return cfg
        time.sleep(1)
    return None


def is_admin():
    try:
        import ctypes
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def renew_dhcp():
    """Release and renew the lease (needs Administrator). True if a valid IP comes back."""
    adapter = get_interface_info().get("Name", "Wi-Fi")
    run_command(f'ipconfig /release "{adapter}"')
    run_command(f'ipconfig /renew "{adapter}"', timeout=60)
    return wait_for_ip(timeout=20) is not None


def ping_ok(host, count=4):
    return "(0% loss)" in run_command(f"ping -n {count} {host}", timeout=60).stdout


def dns_ok(name="google.com"):
    out = run_command(f"nslookup {name}").stdout
    return "Name:" in out and bool(re.search(r"Address(es)?:\s*\S", out.split("Name:", 1)[1]))
