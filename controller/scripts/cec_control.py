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

# ----------------- Pure CLI-Ready Functions -----------------

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
    return quick_scan_results()

# ----------------- Existing UI-Bound Functions -----------------

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

def check_ssdp(ip):
    cmd = 'echo -e "M-SEARCH * HTTP/1.1\\r\\nHOST: 239.255.255.250:1900\\r\\nMAN: \"ssdp:discover\"\\r\\nMX: 1\\r\\nST: ssdp:all\\r\\n\\r\\n" | nc -u -w1 ' + ip + ' 1900'
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=1)
        return "LOCATION:" in result.stdout
    except Exception:
        return False

def check_mdns(ip):
    cmd = f"dig @{ip} -p 5353 some.local"
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=1)
        return "ANSWER:" in result.stdout
    except Exception:
        return False

def check_port(ip, port):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(2)
        s.connect((ip, port))
        s.close()
        return True
    except Exception:
        return False

def ping_ip(ip):
    return os.system(f"ping -c 1 -W 1 {ip} > /dev/null 2>&1") == 0

def check_adb_port(ip):
    device_str = f"{ip}:5555"
    cmd = f"adb -s {device_str} get-state"
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=3)
        if result.returncode == 0 and result.stdout.strip().lower() == "device":
            return True
        if "unauthorized" in result.stderr.lower():
            return True
    except Exception:
        pass
    return False

def save_adb_devices(devices):
    config = configparser.ConfigParser()
    config.read("config.ini")
    if not config.has_section("ADB_Devices"):
        config.add_section("ADB_Devices")
    for i, device in enumerate(devices):
        config["ADB_Devices"][f"device_{i}"] = device
    with open("config.ini", "w") as configfile:
        config.write(configfile)
    logging.info(f"Saved {len(devices)} ADB devices to config.ini.")

def update_adb_dropdown(adb_dropdown):
    config = configparser.ConfigParser()
    config.read("config.ini")
    adb_devices = config["ADB_Devices"] if "ADB_Devices" in config else {}
    adb_dropdown["values"] = list(adb_devices.values())
    logging.info("ADB dropdown updated.")

def quick_scan_active_ips(active_ips_listbox, adb_dropdown):
    local_ip = get_local_ip()
    subnet = ".".join(local_ip.split(".")[:3])
    ips = [f"{subnet}.{i}" for i in range(1, 255)]
    active_ips = []
    with ThreadPoolExecutor(max_workers=50) as executor:
        results = list(executor.map(ping_ip, ips))
    for ip, active in zip(ips, results):
        if active:
            active_ips.append(ip)
    active_ips_listbox.delete(0, tk.END)
    for ip in active_ips:
        ssdp = "SSDP:Active" if check_ssdp(ip) else "SSDP:None"
        mdns = "mDNS:Active" if check_mdns(ip) else "mDNS:None"
        display_str = f"{ip} ({ssdp}, {mdns})"
        active_ips_listbox.insert(tk.END, display_str)
    adb_ips = [ip for ip in active_ips if check_adb_port(ip)]
    adb_list = [f"{ip}:5555" for ip in adb_ips]
    save_adb_devices(adb_list)
    update_adb_dropdown(adb_dropdown)

def scan_network_for_adb(active_ips_listbox, adb_dropdown):
    local_ip = get_local_ip()
    subnet = ".".join(local_ip.split(".")[:3])
    active_ips = []
    for i in range(1, 255):
        ip = f"{subnet}.{i}"
        if os.system(f"ping -c 1 -W 1 {ip} > /dev/null 2>&1") == 0:
            active_ips.append(ip)
    active_ips_listbox.delete(0, tk.END)
    for ip in active_ips:
        ssdp = "SSDP:Active" if check_ssdp(ip) else "SSDP:None"
        mdns = "mDNS:Active" if check_mdns(ip) else "mDNS:None"
        display_str = f"{ip} ({ssdp}, {mdns})"
        active_ips_listbox.insert(tk.END, display_str)
    adb_ips = [ip for ip in active_ips if check_adb_port(ip)]
    adb_list = [f"{ip}:5555" for ip in adb_ips]
    save_adb_devices(adb_list)
    update_adb_dropdown(adb_dropdown)

def deep_scan(active_ips_listbox, adb_dropdown):
    scan_network_for_adb(active_ips_listbox, adb_dropdown)

def connect_to_adb(adb_dropdown):
    adb_target = adb_dropdown.get()
    if adb_target:
        os.system(f"adb disconnect {adb_target}")
        time.sleep(1)
        os.system(f"adb connect {adb_target}")
        logging.info(f"Attempting ADB connection to {adb_target}")

def check_adb_on_selected_ip(active_ips_listbox, adb_dropdown):
    selection = active_ips_listbox.curselection()
    if not selection:
        messagebox.showerror("Check ADB", "No IP selected.")
        return
    ip = active_ips_listbox.get(selection[0]).split()[0]
    if check_adb_port(ip):
        current_values = list(adb_dropdown['values'])
        adb_device = f"{ip}:5555"
        if adb_device not in current_values:
            current_values.append(adb_device)
            adb_dropdown['values'] = current_values
        config = configparser.ConfigParser()
        config.read("config.ini")
        if not config.has_section("ADB_Devices"):
            config.add_section("ADB_Devices")
        key = f"device_{len(config['ADB_Devices'])}"
        config["ADB_Devices"][key] = adb_device
        with open("config.ini", "w") as configfile:
            config.write(configfile)
    else:
        messagebox.showerror("Check ADB", f"IP {ip} does not appear to be running ADB on port 5555.")

def scan_service(ip, port, timeout, service_commands):
    service_info = ""
    if port in service_commands:
        service_name, command_template = service_commands[port]
        cmd = command_template.format(ip=ip, timeout=timeout)
        logging.info(f"Scanning {ip} on port {port} ({service_name}) with command: {cmd}")
        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
            output = result.stdout + result.stderr
            if port in [80, 8080, 8008, 7878, 8989, 32400, 8123, 8112, 443]:
                service_info = "Active" if ("200 OK" in output or "HTTP/" in output) else "Inactive"
            elif port == 554:
                service_info = "Active" if "RTSP/1.0" in output else "Inactive"
            elif port == 1935:
                service_info = "Active" if "RTMP" in output else "Inactive"
            elif port == 1900:
                service_info = "Active" if "LOCATION:" in output else "Inactive"
            elif port == 5353:
                service_info = "Active" if ("ANSWER:" in output or "some.local" in output) else "Inactive"
            elif port in [1883, 8883]:
                service_info = "Active" if ("mosquitto" in output or "Connected" in output) else "Inactive"
            elif port == 22:
                service_info = "Active" if output.strip() == "" else "Inactive"
            else:
                service_info = "Checked"
        except subprocess.TimeoutExpired:
            service_info = "Timeout"
        except Exception:
            service_info = "Error"
    else:
        service_info = "N/A"
    return service_info

def custom_search(root, active_ips_listbox, current_task_label, custom_ports, service_commands, global_timeout):
    ips = [item.split()[0] for item in active_ips_listbox.get(0, tk.END)]
    if not ips:
        messagebox.showerror("Custom Search", "No active IPs to scan.")
        return
    result_window = tk.Toplevel(root)
    result_window.title("Custom Port Scan Results")
    columns = ["IP"] + [service_commands[p][0] if p in service_commands else str(p) for p in custom_ports]
    tree = ttk.Treeview(result_window, columns=columns, show="headings")
    for col in columns:
        tree.heading(col, text=col)
        tree.column(col, width=100)
    tree.pack(fill="both", expand=True)
    def scan_ip(ip):
        row = [ip]
        for port in custom_ports:
            status = scan_service(ip, port, global_timeout, service_commands)
            row.append(status)
        tree.insert("", tk.END, values=row)
        logging.info(f"Scanned {ip}: {row[1:]}")
    for ip in ips:
        scan_ip(ip)
    current_task_label.config(text="Custom scan complete.")

# ----------------- CLI Entry Point -----------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Network-scan utilities: quick or deep scan")
    parser.add_argument("mode", choices=["quick", "deep"], help="Which scan to run")
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
