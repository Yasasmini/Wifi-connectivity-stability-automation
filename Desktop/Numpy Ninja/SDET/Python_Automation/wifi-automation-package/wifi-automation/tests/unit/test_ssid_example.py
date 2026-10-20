def test_different_ssid_does_not_match():
    expected_ssid = "ExampleHomeWiFi"
    actual_ssid = "ExampleGuestWiFi"

    assert actual_ssid != expected_ssid