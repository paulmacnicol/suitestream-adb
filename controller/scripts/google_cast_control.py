#!/usr/bin/env python3
import sys
import re
import json
import time
import logging
import argparse
import pychromecast

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

current_cast = None
CONNECT_TIMEOUT = 5
CONNECT_RETRIES = 3
RETRY_DELAY = 2
CAST_PORT = 8009

def is_ip(source):
    """Return True if source looks like an IP or IP:port."""
    return bool(re.match(r'^\d+\.\d+\.\d+\.\d+(:\d+)?$', source))

def list_devices(timeout=5):
    logging.info("Discovering Chromecast devices (timeout=%ds)...", timeout)
    chromecasts, browser = pychromecast.get_chromecasts(timeout=timeout)
    names = [cc.cast_info.friendly_name for cc in chromecasts]
    logging.info("Found devices: %s", names)
    browser.stop_discovery()
    print(json.dumps(names, indent=2))
    return chromecasts

def find_chromecast_by_name(name, timeout=CONNECT_TIMEOUT, retries=CONNECT_RETRIES):
    """Discover and connect to the Chromecast with the given friendly name."""
    for attempt in range(1, retries+1):
        logging.info("Discovering by name '%s' (attempt %d/%d)...", name, attempt, retries)
        chromecasts, browser = pychromecast.get_chromecasts(timeout=timeout)
        target = None
        for cc in chromecasts:
            fn = cc.cast_info.friendly_name
            if fn == name:
                target = cc
                break
        browser.stop_discovery()
        if target:
            try:
                target.wait(timeout=timeout)
                logging.info("Connected to '%s'", name)
                return target
            except Exception as e:
                logging.error("Failed to wait/connect to '%s': %s", name, e)
        if attempt < retries:
            time.sleep(RETRY_DELAY)
    logging.critical("No Chromecast named '%s' found after %d attempts", name, retries)
    sys.exit(1)

def connect_by_ip(host, port=CAST_PORT, timeout=CONNECT_TIMEOUT, retries=CONNECT_RETRIES):
    """Direct IP connect with retries."""
    for attempt in range(1, retries+1):
        try:
            logging.info("Connecting to %s:%d (attempt %d/%d)...", host, port, attempt, retries)
            cc = pychromecast.Chromecast(host=host, port=port, timeout=timeout)
            cc.wait(timeout=timeout)
            logging.info("Connected to '%s' at %s", cc.cast_info.friendly_name, host)
            return cc
        except Exception as e:
            logging.error("Connection attempt %d failed: %s", attempt, e)
            if attempt < retries:
                time.sleep(RETRY_DELAY)
    logging.critical("Failed to connect to Chromecast at %s after %d attempts", host, retries)
    sys.exit(1)

def load_media(url, content_type="video/mp4"):
    logging.info("Loading media '%s' (type=%s)", url, content_type)
    try:
        current_cast.media_controller.play_media(url, content_type=content_type)
        current_cast.media_controller.block_until_active()
        logging.info("Media playback started")
    except Exception as e:
        logging.warning("load_media error: %s -- reconnecting", e)
        reconnect()
        current_cast.media_controller.play_media(url, content_type=content_type)
        current_cast.media_controller.block_until_active()
        logging.info("Media playback started after retry")

def play():
    logging.info("Play command")
    try:
        current_cast.media_controller.play()
    except Exception as e:
        logging.warning("Play error: %s -- reconnecting", e)
        reconnect()
        current_cast.media_controller.play()

def pause():
    logging.info("Pause command")
    try:
        current_cast.media_controller.pause()
    except Exception as e:
        logging.warning("Pause error: %s -- reconnecting", e)
        reconnect()
        current_cast.media_controller.pause()

def stop():
    logging.info("Stop command")
    try:
        current_cast.media_controller.stop()
    except Exception as e:
        logging.warning("Stop error: %s -- reconnecting", e)
        reconnect()
        current_cast.media_controller.stop()

def seek(seconds):
    logging.info("Seek to %s seconds", seconds)
    try:
        current_cast.media_controller.seek(seconds)
    except Exception as e:
        logging.warning("Seek error: %s -- reconnecting", e)
        reconnect()
        current_cast.media_controller.seek(seconds)

def set_volume(level):
    logging.info("Set volume to %s", level)
    try:
        current_cast.set_volume(level)
    except Exception as e:
        logging.warning("Set volume error: %s -- reconnecting", e)
        reconnect()
        current_cast.set_volume(level)

def mute_device(unmute=False):
    action = "Unmuting" if unmute else "Muting"
    logging.info("%s device", action)
    try:
        current_cast.set_volume_muted(not unmute)
    except Exception as e:
        logging.warning("Mute error: %s -- reconnecting", e)
        reconnect()
        current_cast.set_volume_muted(not unmute)

def reconnect():
    """Re‐establish the connection to `current_cast`."""
    global current_cast
    name = current_cast.cast_info.friendly_name
    host = current_cast.host
    port = current_cast.port
    logging.info("Reconnecting to '%s' at %s:%d...", name, host, port)
    current_cast = connect_by_ip(host, port)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Chromecast control CLI')
    sub = parser.add_subparsers(dest='cmd', required=True)

    # list
    sub.add_parser('list', help='Discover Chromecast devices')

    # connect by name
    connect_p = sub.add_parser('connect', help='Resolve and connect by friendly name')
    connect_p.add_argument('name', help='Friendly name of the Chromecast')

    # other commands need -s/--source
    def add_common(cmd, help_text):
        p = sub.add_parser(cmd, help=help_text)
        p.add_argument('-s', '--source', required=True,
                       help='Name or IP of Chromecast (e.g. "Bedroom TV" or 192.168.0.175)')
        return p

    load_p = add_common('load', 'Load media URL')
    load_p.add_argument('url', help='Media URL to load')
    load_p.add_argument('--type', default='video/mp4', help='Content type')

    add_common('play', 'Play media')
    add_common('pause', 'Pause media')
    add_common('stop', 'Stop media')

    seek_p = add_common('seek', 'Seek to position')
    seek_p.add_argument('seconds', type=float, help='Seconds to seek to')

    vol_p = add_common('vol', 'Set volume level')
    vol_p.add_argument('level', type=float, help='Volume level between 0.0 and 1.0')

    mute_p = add_common('mute', 'Mute/unmute')
    mute_p.add_argument('--unmute', action='store_true',
                        help='If set, unmute instead of mute')

    args = parser.parse_args()

    # LIST
    if args.cmd == 'list':
        list_devices()
        sys.exit(0)

    # CONNECT
    if args.cmd == 'connect':
        cc = find_chromecast_by_name(args.name)
        sys.exit(0)

    # OTHER COMMANDS
    source = args.source
    if is_ip(source):
        host, *port = source.split(':')
        port = int(port[0]) if port else CAST_PORT
        current_cast = connect_by_ip(host, port)
    else:
        current_cast = find_chromecast_by_name(source)

    # DISPATCH
    if args.cmd == 'load':
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
        mute_device(unmute=args.unmute)

    logging.info("Command '%s' completed", args.cmd)
