#!/usr/bin/env python3
import sys
import logging
import argparse
import json
import time

import pychromecast
from pychromecast.discovery import discover_listed_chromecasts

#─── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

#─── Constants ────────────────────────────────────────────────────────────────
DISCOVER_TIMEOUT = 5       # seconds to wait for discovery
CONNECT_TIMEOUT  = 5       # seconds for Chromecast.connect()
RETRY_DELAY      = 2       # retry delay for discovery

#─── Discovery & Connection Helpers ──────────────────────────────────────────
def discover_devices(friendly_names=None, timeout=DISCOVER_TIMEOUT):
    """
    Discover Chromecasts, optionally filtering to a list of friendly_names.
    Returns (devices, browser) so caller can stop_discovery(browser).
    """
    devices, browser = discover_listed_chromecasts(
        friendly_names=friendly_names or [],
        timeout=timeout
    )
    return devices, browser

def find_device(name):
    """Find one Chromecast by friendly_name, exit if not found."""
    logging.info("Looking for Chromecast named %r...", name)
    devices, browser = discover_devices(friendly_names=[name])
    # stop the background discovery
    browser.stop_discovery()
    for d in devices:
        if d.friendly_name == name:
            logging.info("Found %r at %s:%d", d.friendly_name, d.host, d.port)
            return d
    logging.error("No Chromecast named %r found", name)
    sys.exit(1)

def connect_to(device_info):
    """
    Given a ChromecastInfo (with .host/.port), open a socket,
    wait for status, and return a live Chromecast client.
    """
    logging.info("Connecting to %r...", device_info.friendly_name)
    cc = pychromecast.Chromecast(
        host=device_info.host,
        port=device_info.port,
        timeout=CONNECT_TIMEOUT
    )
    cc.wait(timeout=CONNECT_TIMEOUT)
    logging.info("Connected to %r", device_info.friendly_name)
    return cc

#─── Main CLI ─────────────────────────────────────────────────────────────────
def main():
    p = argparse.ArgumentParser(description="Chromecast control CLI")
    sub = p.add_subparsers(dest="cmd", required=True)

    # list
    sub.add_parser('list', help="Discover all Chromecast devices")

    # connect
    conn_p = sub.add_parser('connect', help="Do a one-off connect/test handshake")
    conn_p.add_argument('name', help="Friendly name exactly as in `list`")

    # load media
    load_p = sub.add_parser('load', help="Load media URL")
    load_p.add_argument('-s', '--source', required=True, help="Friendly name of target device")
    load_p.add_argument('url', help="Media URL to load")
    load_p.add_argument('--type', default='video/mp4', help="Content type")

    # simple media commands
    for cmd in ('play','pause','stop'):
        c = sub.add_parser(cmd, help=f"{cmd.capitalize()} media")
        c.add_argument('-s','--source',required=True,help="Friendly name of target device")

    # seek
    seek_p = sub.add_parser('seek', help="Seek to position (seconds)")
    seek_p.add_argument('-s','--source',required=True,help="Friendly name of target device")
    seek_p.add_argument('seconds',type=float,help="Seconds to seek to")

    # volume
    vol_p = sub.add_parser('vol', help="Set volume level (0.0–1.0)")
    vol_p.add_argument('-s','--source',required=True,help="Friendly name of target device")
    vol_p.add_argument('level',type=float,help="Volume level between 0.0 and 1.0")

    # mute/unmute
    mute_p = sub.add_parser('mute', help="Mute or unmute")
    mute_p.add_argument('-s','--source',required=True,help="Friendly name of target device")
    mute_p.add_argument('--unmute',action='store_true',help='Unmute instead of mute')

    args = p.parse_args()

    # ─────────────── LIST ─────────────────────
    if args.cmd == 'list':
        devices, browser = discover_devices(timeout=DISCOVER_TIMEOUT)
        browser.stop_discovery()
        names = [d.friendly_name for d in devices]
        print(json.dumps(names, indent=2))
        sys.exit(0)

    # ───────────── CONNECT ────────────────────
    if args.cmd == 'connect':
        device_info = find_device(args.name)
        cc = connect_to(device_info)
        # once we've done the handshake, exit
        sys.exit(0)

    # ───────────── MEDIA COMMANDS ─────────────
    # For all other commands we need to discover & connect
    # by `args.source` then invoke the correct method on `cc`
    device_info = find_device(args.source)
    cc = connect_to(device_info)
    mc = cc.media_controller
    status = cc.status  # up-to-date after cc.wait()

    try:
        if args.cmd == 'load':
            logging.info("Loading media '%s' (type=%s)", args.url, args.type)
            mc.play_media(args.url, content_type=args.type)
            mc.block_until_active()
        elif args.cmd == 'play':
            mc.play()
        elif args.cmd == 'pause':
            mc.pause()
        elif args.cmd == 'stop':
            mc.stop()
        elif args.cmd == 'seek':
            logging.info("Seeking to %s seconds", args.seconds)
            mc.seek(args.seconds)
        elif args.cmd == 'vol':
            logging.info("Setting volume to %s", args.level)
            cc.set_volume(args.level)
        elif args.cmd == 'mute':
            action = not args.unmute
            logging.info("%s the device", "Muting" if action else "Unmuting")
            cc.set_volume_muted(action)
        else:
            logging.error("Unknown command: %s", args.cmd)
            sys.exit(1)

        logging.info("Command '%s' completed", args.cmd)
    except Exception as e:
        logging.error("Error running %s: %s", args.cmd, e)
        sys.exit(1)

if __name__ == '__main__':
    main()
