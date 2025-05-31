#!/usr/bin/env bash

# Suitestream First‐boot & Every‐boot Orchestrator with iw‐based Wi-Fi Scan and Debug Logging
LOGFILE=/tmp/suitestream-setup.log
exec >> "$LOGFILE" 2>&1

echo "\n---- suitestream-setup start: $(date) ----"

# 1) Test for Internet connectivity
if ping -c1 -W1 8.8.8.8 >/dev/null 2>&1; then
  echo "↗ Internet reachable → starting Docker stack"
  docker compose -f /opt/suitestream/docker-compose.yml up -d \
    || echo "⚠ docker compose up failed; will retry on next boot"
  exit 0
fi

echo "⛔ No Internet → stopping containers & preparing AP"

docker compose -f /opt/suitestream/docker-compose.yml down || true

# -- tell NM not to touch wlan0 during our AP phase --
nmcli device set wlan0 managed no || true


# 2) Ensure portal directory and clear old scans
mkdir -p /opt/suitestream/portal
rm -f /opt/suitestream/portal/ssids.txt /tmp/ssids_debug.txt

echo "→ Stopping services to free wlan0 for scan"
systemctl stop hostapd dnsmasq avahi-daemon wpa_supplicant || true

echo "🔓 Unblocking Wi-Fi radio"
rfkill unblock wifi

# 3) Prepare interface for scanning
echo "→ Interface down & switch to managed mode"
ip link set wlan0 down || true
iw dev wlan0 set type managed || true
ip link set wlan0 up || true

# 4) Perform iw scan and log results
echo "→ Scanning Wi-Fi networks with iw (may take some seconds...)"
iw dev wlan0 scan \
  | grep -E "SSID: " \
  | sed 's/^.*SSID: //' \
  | sort -u \
  | tee /opt/suitestream/portal/ssids.txt /tmp/ssids_debug.txt \
    || echo "! iw scan listing failed"
test -s /opt/suitestream/portal/ssids.txt || echo "! ssids.txt is empty"

# 5) Switch back to AP mode
echo "→ Reconfiguring wlan0 for AP"
ip link set wlan0 down || true
ip link set wlan0 up
ip addr flush dev wlan0
ip addr add 192.168.50.1/24 dev wlan0

# 6) Restart services for AP & captive-portal
echo "→ Starting hostapd"
systemctl start hostapd       || echo "⚠ hostapd start failed"
echo "→ Starting dnsmasq"
systemctl start dnsmasq       || echo "⚠ dnsmasq start failed"
echo "→ Starting avahi"
systemctl start avahi-daemon  || echo "⚠ avahi start failed"

echo "---- suitestream-setup end: $(date) ----"
exit 0
