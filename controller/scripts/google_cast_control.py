#!/usr/bin/env python3
import sys
import os
import logging
import json
import argparse
import pychromecast
import tkinter as tk
from tkinter import messagebox, simpledialog

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s [%(levelname)s] %(message)s")

current_cast = None

# ----------------- Core Chromecast Functions -----------------

def list_devices(timeout=5):
    """Discover and return available Chromecast devices."""
    chromecasts, browser = pychromecast.get_chromecasts(timeout=timeout)
    return chromecasts


def select_device_by_name(name, timeout=10):
    """Select and connect to a Chromecast by friendly name."""
    global current_cast
    chromecasts, browser = pychromecast.get_chromecasts(timeout=timeout)
    for cc in chromecasts:
        if cc.cast_info.friendly_name == name:
            current_cast = cc
            current_cast.wait()
            return current_cast
    raise ValueError(f"Device '{name}' not found")


def load_media(url, content_type="video/mp4"):
    """Load media URL onto the current cast."""
    if not current_cast:
        raise RuntimeError("No cast selected")
    current_cast.media_controller.play_media(url, content_type=content_type)
    current_cast.media_controller.block_until_active()


def play():
    if current_cast:
        current_cast.media_controller.play()


def pause():
    if current_cast:
        current_cast.media_controller.pause()


def stop():
    if current_cast:
        current_cast.media_controller.stop()


def seek(seconds):
    if current_cast:
        current_cast.media_controller.seek(seconds)


def set_volume(level):
    if current_cast:
        current_cast.set_volume(level)


def mute(muted=True):
    if current_cast:
        current_cast.set_volume_muted(muted)

# ----------------- GUI Functions (unchanged) -----------------

def set_current_cast(cc):
    global current_cast
    current_cast = cc
    try:
        current_cast.wait()
    except Exception as e:
        logging.error("Error during cast.wait(): %s", e)
        messagebox.showerror("Error", f"Error waiting for device: {e}")
        return
    try:
        logging.debug("Now connected to: %s", current_cast.cast_info.friendly_name)
    except Exception:
        pass
    try:
        current_cast.start_pairing()
        code = simpledialog.askstring("Pairing", "Enter verification code (if required):")
        if code and code.strip():
            current_cast.finish_pairing(code)
    except Exception:
        pass


def update_receiver_status(status_var, root):
    if current_cast:
        try:
            st = current_cast.status
            status_var.set(f"Receiver: {st.status_text or 'Idle'} | Volume: {st.volume_level:.2f} (muted: {st.volume_muted})")
        except Exception:
            status_var.set("Error getting receiver status")
    root.after(5000, lambda: update_receiver_status(status_var, root))


def update_media_status(media_status_var, root):
    if current_cast:
        try:
            mc = current_cast.media_controller.status
            media_status_var.set(f"State: {mc.player_state} | Time: {mc.current_time}/{mc.duration}")
        except Exception:
            media_status_var.set("Error getting media status")
    root.after(5000, lambda: update_media_status(media_status_var, root))


def build_cast_controller(parent):
    frame = tk.Frame(parent, padx=10, pady=10)
    frame.pack(fill="both", expand=True)
    # ... GUI build unchanged (omitted for brevity) ...
    pass

# ----------------- CLI Entry Point -----------------
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Chromecast control CLI')
    sub = parser.add_subparsers(dest='cmd', required=True)

    sub.add_parser('list', help='List available Chromecast devices')

    sel = sub.add_parser('select', help='Select a Chromecast by name')
    sel.add_argument('name', help='Friendly name of device')

    load = sub.add_parser('load', help='Load media URL')
    load.add_argument('url', help='Media URL to load')
    load.add_argument('--type', default='video/mp4', help='Content type')

    sub.add_parser('play', help='Play media')
    sub.add_parser('pause', help='Pause media')
    sub.add_parser('stop', help='Stop media')

    seek_p = sub.add_parser('seek', help='Seek to seconds')
    seek_p.add_argument('seconds', type=float, help='Seconds to seek to')

    vol = sub.add_parser('vol', help='Set volume')
    vol.add_argument('level', type=float, help='Volume level 0.0-1.0')

    mute_p = sub.add_parser('mute', help='Mute/unmute')
    mute_p.add_argument('--unmute', action='store_true', help='Unmute if set')

    args = parser.parse_args()
    if args.cmd == 'list':
        devices = list_devices()
        print(json.dumps([cc.cast_info.friendly_name for cc in devices], indent=2))
    elif args.cmd == 'select':
        select_device_by_name(args.name)
    elif args.cmd == 'load':
        load_media(args.url, args.type)
    elif args.cmd == 'play':
        play()
    elif args.cmd == 'pause':
        pause()
    elif args.cmd == 'stop':
        stop()
    elif args.cmd == 'seek':
        seek(args.seconds)
    elif args.cmd == 'vol':
        set_volume(args.level)
    elif args.cmd == 'mute':
        mute(not args.unmute)
