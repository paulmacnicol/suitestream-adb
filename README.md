# Suitestream-ADB

This repository contains all of the configuration and code for the “Suitestream” Raspberry Pi appliance:

- **/etc/**: static‐IP, hostapd, dnsmasq, systemd unit files  
- **/usr-local-bin/**: orchestrator script (`suitestream-setup.sh`), reset script (`reset-wifi.sh`)  
- **/opt-suitestream/**: captive-portal Node/Express app (`server.js`, `package.json`), Docker Compose stack (`docker-compose.yml`), and persistent data folder.

## How it works

1. On every boot, `suitestream-setup.service` runs `suitestream-setup.sh`:  
   - If Internet is up (via `nm-online`), it launches `docker compose up -d`.  
   - Otherwise, it stops containers, scans Wi-Fi, writes `/opt/suitestream/portal/ssids.txt`, configures `wlan0` to `192.168.50.1/24`, and starts `hostapd`, `dnsmasq`, and `avahi-daemon` to present an AP + captive portal.

2. When a user connects to “Suitestream Setup” (wlan0) and visits `http://suitestream.local/`, the Node Express app in `/opt/suitestream/portal/server.js` presents a dropdown of SSIDs.  
   - On POST `/connect`, it stops AP services, unblocks wifi, brings `wlan0` into managed mode, starts `wpa_supplicant`, runs `nmcli device wifi rescan` + `nmcli device wifi connect <SSID> password <password>`, then reboots.

3. On reboot, if that network is now online, the orchestrator’s `nm-online` test passes, and the Pi runs the Docker stack instead of showing the AP.

## File/Folder Map

/etc/
├── dhcpcd.conf
├── hostapd/hostapd.conf
├── dnsmasq.d/suitestream.conf
└── systemd/
├── suitestream-setup.service
└── suitestream-portal.service

/usr-local-bin/
├── suitestream-setup.sh
└── reset-wifi.sh

/opt-suitestream/
├── portal/
│ ├── package.json
│ ├── server.js
│ └── ssids.txt
├── docker-compose.yml
└── data/ (optional persistent data)

