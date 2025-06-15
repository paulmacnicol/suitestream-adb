#!/usr/bin/env python3
import os
import socket
import subprocess
import logging
import time
import configparser
import json
from concurrent.futures import ThreadPoolExecutor
import tkinter as tk
from tkinter import messagebox, ttk
import argparse

# ----------------- Pure, CLI‐Ready Functions -----------------

def quick_scan_results():
    """Return list of dicts for each alive IP in local /24 subnet."""
    local_ip = get_local_ip()
    subnet = ".".join(local_ip.split(".")[:3])
    ips = [f"{subnet}.{i}" for i in range(1, 255)]
    active = []
    with ThreadPoolExecutor(max_workers=50) as executor:
        results = list(executor.map(ping_ip, ips))
    for ip, alive in zip(ips, results):
        if alive:
            active.append(ip)

    output = []
    for ip in active:
        output.append({
            "ip": ip,
            "ssdp": check_ssdp(ip),
            "mdns": check_mdns(ip),
            "adb": check_adb_port(ip)
        })
    return output


def deep_scan_results():
    """Sequential scan: equivalent to quick_scan_results."""
    # For simplicity, reuse quick version (sequential fallback could be implemented if needed)
    return quick_scan_results()


# ----------------- Existing UI‐Bound Functions -----------------

def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        logging.info(f"Local IP determined: {local_ip}")
        return local_ip
    except Exception as e:
        logging.error(f"Error getting local IP: {e}")
        return "127.0.0.1"
    finally:
        s.close()

# ... (rest of existing functions unchanged) ...

def check_ssdp(ip):
    cmd = 'echo -e "M-SEARCH * HTTP/1.1\\r\\nHOST: 239.255.255.250:1900\\r\\nMAN: \"ssdp:discover\"\\r\\nMX: 1\\r\\nST: ssdp:all\\r\\n\\r\\n" | nc -u -w1 ' + ip + ' 1900'
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=1)
        return "LOCATION:" in result.stdout
    except Exception:
        return False

# [Include all other existing functions exactly as before]
# ping_ip, check_mdns, check_port, check_adb_port,
# save_adb_devices, update_adb_dropdown, quick_scan_active_ips,
# scan_network_for_adb, deep_scan, connect_to_adb,
# check_adb_on_selected_ip, scan_service, custom_search

# ----------------- CLI Entry Point -----------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Network-scan utilities: quick or deep scan")
    parser.add_argument("mode", choices=["quick","deep"], help="Which scan to run")
    parser.add_argument("--json", action="store_true", help="Output in JSON format")
    args = parser.parse_args()

    if args.mode == "quick":
        result = quick_scan_results()
    else:
        result = deep_scan_results()

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        for entry in result:
            print(f"{entry['ip']}\tSSDP={entry['ssdp']}\tmDNS={entry['mdns']}\tADB={entry['adb']}")
