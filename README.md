# wifi-connectivity-stability-automation

Python + pytest framework that tests the full Wi-Fi connection flow of a Windows client
against a real router, from the AP's **beacon** to a working **IP connection**, and produces an HTML report.

## What it tests

| Stage | What happens | Tests | How it is checked (Windows) |
|---|---|---|---|
| 1. Beacon / scan | AP advertises SSID, security, channel, radio | `test_01_beacon_scan.py` | `netsh wlan show networks mode=bssid` |
| 3-5. Authentication, association, 4-way handshake | Link comes up (wrong password fails here) | `test_02_link_up.py`, `test_04_negative.py` | `netsh wlan connect`, `show interfaces` |
| 6. DHCP | Client gets IP, gateway, DHCP server | `test_03_ip_connectivity.py` | `ipconfig /all` |
| 7-8. Gateway, DNS, internet | Traffic really flows | `test_03_ip_connectivity.py` | `ping`, `nslookup` |
| Stability | Connection time, repeated reconnects with IP check | `test_05_stability.py` | repeated connect/disconnect |

`tests/unit/` checks the parsers with sample output and mocks (no hardware needed).
Failing hardware tests save `netsh`/`ipconfig` output to `logs/`.

## Setup
1. Windows laptop, Python 3, one Wi-Fi router.
2. `python -m venv venv` then `venv\Scripts\activate`
3. `pip install -r requirements.txt`
4. Copy `config.example.yaml` to `config.yaml` and fill in your SSID, profile name, router IP.
   Connect to the network once so Windows saves the profile (`netsh wlan show profiles`).

## Run
- Parser tests only: `pytest -m unit`
- Device tests: `pytest -m hardware -s`   (use an Administrator terminal for the DHCP renew test)
- Everything: `pytest -s`
- Report: `reports/report.html`

## Limits
One router and one Windows client. Windows reports the outcome of each Wi-Fi stage but not the
individual beacon/auth/association/EAPOL frames; for frame-level checks add a monitor-mode
adapter with Wireshark. Roaming and multi-AP interoperability are not covered.
## CI Pipeline

GitHub Actions runs unit tests and packages the project after successful checks.
