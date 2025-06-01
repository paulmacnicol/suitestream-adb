#!/usr/bin/env bash
#
# collect-all.sh
# Copies the live Suitestream files from /etc, /usr/local/bin, and /opt/suitestream
# into the Git repo at /home/gc/suitestream-adb, preserving directory structure.
#
# Run this from the repo directory (or with full path). It must be run as root (sudo).

set -e

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
echo
echo "============================================="
echo " Collecting Suitestream files into Git repo "
echo "   Repo location: $REPO_DIR"
echo "============================================="
echo

# 1) Ensure target subdirectories exist under the repo
mkdir -p "$REPO_DIR/etc/hostapd"
mkdir -p "$REPO_DIR/etc/dnsmasq.d"
mkdir -p "$REPO_DIR/etc/systemd"
mkdir -p "$REPO_DIR/usr-local-bin"
mkdir -p "$REPO_DIR/opt-suitestream/portal"
mkdir -p "$REPO_DIR/opt-suitestream/data"

# 2) Copy /etc files
echo "-- Copying /etc/dhcpcd.conf → $REPO_DIR/etc/dhcpcd.conf"
if [ -f /etc/dhcpcd.conf ]; then
  cp /etc/dhcpcd.conf "$REPO_DIR/etc/dhcpcd.conf"
else
  echo "   (warning: /etc/dhcpcd.conf not found)"
fi

echo "-- Copying /etc/hostapd/hostapd.conf → $REPO_DIR/etc/hostapd/hostapd.conf"
if [ -f /etc/hostapd/hostapd.conf ]; then
  cp /etc/hostapd/hostapd.conf "$REPO_DIR/etc/hostapd/hostapd.conf"
else
  echo "   (warning: /etc/hostapd/hostapd.conf not found)"
fi

echo "-- Copying /etc/dnsmasq.d/suitestream.conf → $REPO_DIR/etc/dnsmasq.d/suitestream.conf"
if [ -f /etc/dnsmasq.d/suitestream.conf ]; then
  cp /etc/dnsmasq.d/suitestream.conf "$REPO_DIR/etc/dnsmasq.d/suitestream.conf"
else
  echo "   (warning: /etc/dnsmasq.d/suitestream.conf not found)"
fi

echo "-- Copying systemd unit: suitestream-setup.service"
if [ -f /etc/systemd/system/suitestream-setup.service ]; then
  cp /etc/systemd/system/suitestream-setup.service "$REPO_DIR/etc/systemd/suitestream-setup.service"
else
  echo "   (warning: /etc/systemd/system/suitestream-setup.service not found)"
fi

echo "-- Copying systemd unit: suitestream-portal.service"
if [ -f /etc/systemd/system/suitestream-portal.service ]; then
  cp /etc/systemd/system/suitestream-portal.service "$REPO_DIR/etc/systemd/suitestream-portal.service"
else
  echo "   (warning: /etc/systemd/system/suitestream-portal.service not found)"
fi

echo "-- Copying wpa_supplicant@.service (if present)"
if [ -f /etc/systemd/system/wpa_supplicant@.service ]; then
  cp /etc/systemd/system/wpa_supplicant@.service "$REPO_DIR/etc/systemd/wpa_supplicant@.service"
else
  echo "   (info: /etc/systemd/system/wpa_supplicant@.service not present)"
fi

# 3) Copy /usr/local/bin scripts
echo "-- Copying /usr/local/bin/suitestream-setup.sh → $REPO_DIR/usr-local-bin/suitestream-setup.sh"
if [ -f /usr/local/bin/suitestream-setup.sh ]; then
  cp /usr/local/bin/suitestream-setup.sh "$REPO_DIR/usr-local-bin/suitestream-setup.sh"
else
  echo "   (warning: /usr/local/bin/suitestream-setup.sh not found)"
fi

echo "-- Copying /usr/local/bin/reset-wifi.sh → $REPO_DIR/usr-local-bin/reset-wifi.sh"
if [ -f /usr/local/bin/reset-wifi.sh ]; then
  cp /usr/local/bin/reset-wifi.sh "$REPO_DIR/usr-local-bin/reset-wifi.sh"
else
  echo "   (warning: /usr/local/bin/reset-wifi.sh not found)"
fi

# 4) Copy /opt/suitestream content
echo "-- Copying /opt/suitestream/docker-compose.yml → $REPO_DIR/opt-suitestream/docker-compose.yml"
if [ -f /opt/suitestream/docker-compose.yml ]; then
  cp /opt/suitestream/docker-compose.yml "$REPO_DIR/opt-suitestream/docker-compose.yml"
else
  echo "   (warning: /opt/suitestream/docker-compose.yml not found)"
fi

echo "-- Copying /opt/suitestream/portal/package.json → $REPO_DIR/opt-suitestream/portal/package.json"
if [ -f /opt/suitestream/portal/package.json ]; then
  cp /opt/suitestream/portal/package.json "$REPO_DIR/opt-suitestream/portal/package.json"
else
  echo "   (warning: /opt/suitestream/portal/package.json not found)"
fi

echo "-- Copying /opt/suitestream/portal/server.js → $REPO_DIR/opt-suitestream/portal/server.js"
if [ -f /opt/suitestream/portal/server.js ]; then
  cp /opt/suitestream/portal/server.js "$REPO_DIR/opt-suitestream/portal/server.js"
else
  echo "   (warning: /opt/suitestream/portal/server.js not found)"
fi

echo "-- Copying /opt/suitestream/portal/ssids.txt (if present) → $REPO_DIR/opt-suitestream/portal/ssids.txt"
if [ -f /opt/suitestream/portal/ssids.txt ]; then
  cp /opt/suitestream/portal/ssids.txt "$REPO_DIR/opt-suitestream/portal/ssids.txt"
else
fi
