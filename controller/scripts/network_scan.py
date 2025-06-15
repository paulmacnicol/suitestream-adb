#!/usr/bin/env python3
import os
import socket
import subprocess
import logging
import argparse
import json
from concurrent.futures import ThreadPoolExecutor

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# ----------------- Core Functions -----------------

def ping_ip(ip):
    """Return True if the host responds to a single ping."""
    return os.system(f"ping -c 1 -W 1 {ip} > /dev/null 2>&1") == 0


def get_local_ip():
    """Determine local machine's IP address."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"
    finally:
        s.close()


def check_ssdp(ip):
    """Return True if SSDP discovery returns a LOCATION header."""
    cmd = ('echo -e "M-SEARCH * HTTP/1.1\r\n'
           'HOST: 239.255.255.250:1900\r\nMAN: \"ssdp:discover\"\r\n'
           'MX: 1\r\nST: ssdp:all\r\n\r\n"'
           f' | nc -u -w1 {ip} 1900')
    try:
        out = subprocess.check_output(cmd, shell=True, stderr=subprocess.DEVNULL, timeout=2, text=True)
        return "LOCATION:" in out
    except Exception:
        return False


def check_mdns(ip):
    """Return True if mDNS query returns an ANSWER section."""
    cmd = f"dig @{ip} -p 5353 some.local +timeout=2 +tries=1"
    try:
        out = subprocess.check_output(cmd, shell=True, stderr=subprocess.DEVNULL, timeout=3, text=True)
        return "ANSWER:" in out
    except Exception:
        return False


def check_adb_port(ip):
    """Return True if ADB on port 5555 is available (device or unauthorized)."""
    target = f"{ip}:5555"
    cmd = f"adb -s {target} get-state"
    try:
        proc = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=3)
        if proc.returncode == 0 and proc.stdout.strip().lower() == 'device':
            return True
        if 'unauthorized' in proc.stderr.lower():
            return True
    except Exception:
        pass
    return False

# ----------------- Scan Functions -----------------

def quick_scan_results():
    """Perform a parallel scan of local /24 subnet for ping, SSDP, mDNS, and ADB."""
    local_ip = get_local_ip()
    subnet = '.'.join(local_ip.split('.')[:3])
    ips = [f"{subnet}.{i}" for i in range(1, 255)]
    with ThreadPoolExecutor(max_workers=50) as executor:
        alive = list(executor.map(ping_ip, ips))
    results = []
    for ip, up in zip(ips, alive):
        if up:
            results.append({
                'ip': ip,
                'ssdp': check_ssdp(ip),
                'mdns': check_mdns(ip),
                'adb': check_adb_port(ip)
            })
    return results


def deep_scan_results():
    """Sequential scan of local /24 subnet (currently alias for quick)."""
    return quick_scan_results()

# ----------------- CLI Entry Point -----------------

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Network Scan CLI: quick or deep')
    parser.add_argument('mode', choices=['quick', 'deep'], help='Scan mode')
    parser.add_argument('--json', action='store_true', help='Output results in JSON')
    args = parser.parse_args()

    if args.mode == 'quick':
        output = quick_scan_results()
    else:
        output = deep_scan_results()

    if args.json:
        print(json.dumps(output, indent=2))
    else:
        for entry in output:
            print(f"{entry['ip']}\tSSDP={entry['ssdp']}\tmDNS={entry['mdns']}\tADB={entry['adb']}")
