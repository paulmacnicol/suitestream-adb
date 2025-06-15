#!/usr/bin/env python3
import subprocess
import re
import json
import os
import argparse
from tkinter import messagebox

# Load vendor lookup from file, or use a default small lookup.
lookup_file = "vendor_lookup.json"
if os.path.exists(lookup_file):
    with open(lookup_file, "r") as f:
        vendor_lookup = json.load(f)
else:
    vendor_lookup = {
        "6673": "Chromecast",
        "7173227": "Panasonic"
    }


def run_command(cmd):
    """Run a shell command and return its stdout (or stderr on error)."""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        return e.stderr.strip()


def parse_port_info(dumpsys_output):
    """
    Extracts port information from the mPortInfo block.
    Returns a list of dictionaries with port_id, type, address, cec, arc, mhl.
    """
    ports = []
    port_block = re.search(r"mPortInfo:\s*((?:\s+port_id:.*\n)+)", dumpsys_output)
    if port_block:
        lines = port_block.group(1).strip().splitlines()
        for line in lines:
            port_data = {}
            for part in line.strip().split(","):
                if ":" in part:
                    key, val = part.split(":", 1)
                    port_data[key.strip()] = val.strip()
            if "port_id" in port_data:
                try:
                    port_data["port_id"] = int(port_data["port_id"])
                except ValueError:
                    pass
            for flag in ["cec", "arc", "mhl"]:
                if flag in port_data:
                    port_data[flag] = port_data[flag].lower() == "true"
            ports.append(port_data)
    return ports


def parse_local_device(dumpsys_output):
    """
    Extracts local device info from the HdmiCecLocalDevice block.
    Returns dict with display_name, device_type, logical_address, vendor_id, physical_address, mac_address.
    """
    local_dev = {}
    m = re.search(r"HdmiCecLocalDevice #\d+:\n((?: {4}.*\n)+)", dumpsys_output)
    if m:
        block = m.group(1)
        info = re.search(r"mDeviceInfo:\s*(CEC:.*)", block)
        if info:
            line = info.group(1)
            local_dev["logical_address"] = re.search(r"logical_address:\s*(0x[0-9A-Fa-f]+)", line).group(1)
            local_dev["device_type"]     = re.search(r"device_type:\s*(\d+)", line).group(1)
            local_dev["vendor_id"]       = re.search(r"vendor_id:\s*([0-9]+)", line).group(1)
            local_dev["display_name"]    = re.search(r"display_name:\s*(.*?)\s+power_status:", line).group(1)
            local_dev["physical_address"] = re.search(r"physical_address:\s*(0x[0-9A-Fa-f]+)", line).group(1)
            local_dev["mac_address"]     = "Not available"
    return local_dev


def parse_connected_devices(dumpsys_output):
    """
    Parses the "CEC:" lines in the dumpsys output.
    Returns list of devices with logical_address, display_name, device_type, vendor_id, physical_address, port_id, mac_address, manufacturer.
    """
    devices = []
    lines = re.findall(r"CEC:\s+(.*?port_id:\s*-?\d+)", dumpsys_output)
    for line in lines:
        dev = {
            "logical_address": re.search(r"logical_address:\s*(0x[0-9A-Fa-f]+)", line).group(1),
            "display_name":    re.search(r"display_name:\s*(.*?)\s+power_status:", line).group(1),
            "device_type":     re.search(r"device_type:\s*(\d+)", line).group(1),
            "vendor_id":       re.search(r"vendor_id:\s*([0-9]+)", line).group(1),
            "physical_address": re.search(r"physical_address:\s*(0x[0-9A-Fa-f]+)", line).group(1),
            "port_id":         int(re.search(r"port_id:\s*(-?\d+)", line).group(1)),
            "mac_address":     "Not available"
        }
        vid = dev["vendor_id"]
        dev["manufacturer"] = vendor_lookup.get(vid, "Unknown")
        devices.append(dev)
    return devices


def determine_functions(device_type):
    """Return functions string based on CEC device type."""
    return {
        "0": "Power On/Off, Volume, Change Channels",
        "4": "Power On/Off, Volume"
    }.get(device_type, "Unknown functions")


def generate_summary(local_device, ports, connected_devices):
    """Build human-readable summary of HDMI layout."""
    summary = []
    name = local_device.get("display_name", "This device")
    summary.append(f"{name} has {len(ports)} HDMI ports detected.")
    arc = [str(p["port_id"]) for p in ports if p.get("arc")]
    if arc:
        summary.append(f"ARC enabled on ports: {', '.join(arc)}.")
    for p in ports:
        dev = next((d for d in connected_devices if d["port_id"] == p["port_id"]), None)
        if dev:
            funcs = determine_functions(dev["device_type"])
            summary.append(
                f"HDMI{p['port_id']} = {dev['display_name']} | Functions: {funcs} | "
                f"ID: {dev['logical_address']} | Phys Addr: {dev['physical_address']}"
            )
        else:
            summary.append(f"HDMI{p['port_id']} = No device detected.")
    unassigned = [d for d in connected_devices if d['port_id'] == -1]
    if unassigned:
        summary.append("Other detected devices:")
        for d in unassigned:
            funcs = determine_functions(d['device_type'])
            summary.append(
                f"{d['display_name']} | Functions: {funcs} | "
                f"ID: {d['logical_address']} | Phys Addr: {d['physical_address']}"
            )
    return "\n".join(summary)


def scan_cec_layout(device):
    """Scan HDMI-CEC layout for given ADB device and return summary and JSON."""
    dumpsys = run_command(f"adb -s {device} shell dumpsys hdmi_control")
    ports = parse_port_info(dumpsys)
    local = parse_local_device(dumpsys)
    devices = parse_connected_devices(dumpsys)
    props_raw = run_command(f"adb -s {device} shell getprop | grep -i hdmi")
    sys_props = {k:v for line in props_raw.splitlines() if ":" in line
                 for k,v in [line.replace(']','').split('[:',1)]}
    summary = generate_summary(local, ports, devices)
    data = {
        "local_device": local,
        "ports": ports,
        "connected_devices": devices,
        "system_properties": sys_props,
        "summary": summary
    }
    with open("hdmi_layout.json", "w") as f:
        json.dump(data, f, indent=2)
    return data


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="HDMI-CEC layout probe CLI")
    parser.add_argument("device", help="ADB target (e.g. 192.168.1.42:5555)")
    parser.add_argument("--json", action="store_true", help="Output full JSON data")
    args = parser.parse_args()
    result = scan_cec_layout(args.device)
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(result['summary'])
