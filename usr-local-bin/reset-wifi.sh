#!/usr/bin/env bash
set -e

LOG=/tmp/reset-wifi.log
exec &> "$LOG"

echo "---- Reset-WiFi: starting $(date) ----"

# 1) Delete all NM Wi-Fi connection profiles
echo "Deleting NM Wi-Fi profiles…"
for prof in $(nmcli -t -f NAME,TYPE connection show | awk -F: '$2=="wifi"{print $1}'); do
  echo "  • $prof"
  nmcli connection delete "$prof" || true
done

# 2) Remove any leftover system-connections files
echo "Removing leftover connection files…"
rm -f /etc/NetworkManager/system-connections/*.nmconnection 2>/dev/null || true

# 3) Clear wpa_supplicant configs (if any)
echo "Clearing wpa_supplicant configs…"
rm -f /etc/wpa_supplicant/wpa_supplicant-*.conf 2>/dev/null || true

echo "---- Reset-WiFi: complete $(date) ----"
echo "Reboot now to rerun suitestream-setup in AP mode."
