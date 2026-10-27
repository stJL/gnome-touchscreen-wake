#!/usr/bin/python3
"""Wake a GNOME display on touchscreen contact without changing GNOME screensaver state.

Reads the SIS0457 touchscreen via evdev and emits KEY_WAKEUP via /dev/uinput only
when Mutter reports PowerSaveMode=3 (display off). Uses only Python stdlib + gdbus.
"""

import fcntl
import glob
import logging
import os
import re
import signal
import struct
import subprocess
import sys
import time
from pathlib import Path

TOUCH_DEVICE_NAME = "SIS0457:00 0457:11ED"
INPUT_EVENT_STRUCT = struct.Struct("@llHHi")

EV_SYN = 0
EV_KEY = 1
SYN_REPORT = 0
BTN_TOUCH = 330
KEY_WAKEUP = 143

UI_SET_EVBIT = 0x40045564
UI_SET_KEYBIT = 0x40045565
UI_DEV_SETUP = 0x405C5503
UI_DEV_CREATE = 0x5501
UI_DEV_DESTROY = 0x5502

POWER_MODE_ARGS = [
    "gdbus", "call", "--session",
    "--dest", "org.gnome.Mutter.DisplayConfig",
    "--object-path", "/org/gnome/Mutter/DisplayConfig",
    "--method", "org.freedesktop.DBus.Properties.Get",
    "org.gnome.Mutter.DisplayConfig", "PowerSaveMode",
]

# Avoid duplicate wake events while GNOME is updating display state.
TOUCH_DEBOUNCE_SECONDS = 0.25
WAKE_COOLDOWN_SECONDS = 3.0


def setup_logging():
    state_dir = Path.home() / ".local" / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    log_path = state_dir / "touchscreen-wake.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[
            logging.FileHandler(log_path),
            logging.StreamHandler(sys.stderr),
        ],
    )
    logging.info("Starting touchscreen wake helper")
    return log_path


def session_environment():
    env = os.environ.copy()
    runtime_dir = env.get("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}")
    env.setdefault("XDG_RUNTIME_DIR", runtime_dir)
    env.setdefault("DBUS_SESSION_BUS_ADDRESS", f"unix:path={runtime_dir}/bus")
    return env


def find_touchscreen():
    for sys_event in sorted(glob.glob("/sys/class/input/event*")):
        try:
            name = Path(sys_event, "device", "name").read_text().strip()
        except OSError:
            continue
        if name == TOUCH_DEVICE_NAME:
            event_name = Path(sys_event).name
            return f"/dev/input/{event_name}"
    raise FileNotFoundError(
        f"Could not find touchscreen named {TOUCH_DEVICE_NAME!r} under /sys/class/input"
    )


def get_power_mode(env):
    result = subprocess.run(
        POWER_MODE_ARGS,
        capture_output=True,
        text=True,
        timeout=3,
        env=env,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "gdbus query failed")
    match = re.search(r"<(-?\d+)>", result.stdout)
    if not match:
        raise RuntimeError(f"Could not parse PowerSaveMode output: {result.stdout.strip()}")
    return int(match.group(1))


def create_wakeup_device():
    fd = os.open("/dev/uinput", os.O_WRONLY | os.O_NONBLOCK)
    created = False
    try:
        fcntl.ioctl(fd, UI_SET_EVBIT, EV_KEY)
        fcntl.ioctl(fd, UI_SET_KEYBIT, KEY_WAKEUP)
        setup = struct.pack(
            "=HHHH80sI",
            0x06, 0x1234, 0x5678, 1,
            b"T101HA Touch Wake", 0,
        )
        fcntl.ioctl(fd, UI_DEV_SETUP, setup)
        fcntl.ioctl(fd, UI_DEV_CREATE)
        created = True
        time.sleep(0.5)
        logging.info("Created temporary KEY_WAKEUP virtual input device")
        return fd
    except Exception:
        if created:
            try:
                fcntl.ioctl(fd, UI_DEV_DESTROY)
            except OSError:
                pass
        os.close(fd)
        raise


def emit_key(fd, value):
    os.write(fd, INPUT_EVENT_STRUCT.pack(0, 0, EV_KEY, KEY_WAKEUP, value))
    os.write(fd, INPUT_EVENT_STRUCT.pack(0, 0, EV_SYN, SYN_REPORT, 0))


def main():
    log_path = setup_logging()
    env = session_environment()
    input_fd = None
    wake_fd = None
    wake_device_created = False

    # Let SIGTERM unwind through finally, so uinput is cleaned up on service stop.
    signal.signal(signal.SIGTERM, lambda _signum, _frame: sys.exit(0))

    try:
        touch_path = find_touchscreen()
        input_fd = os.open(touch_path, os.O_RDONLY)
        logging.info("Monitoring touchscreen %s (%s)", TOUCH_DEVICE_NAME, touch_path)

        wake_fd = create_wakeup_device()
        wake_device_created = True
        logging.info("Ready; logs: %s", log_path)

        last_touch_check = 0.0
        last_wake = -1e9

        while True:
            raw_event = os.read(input_fd, INPUT_EVENT_STRUCT.size)
            if len(raw_event) != INPUT_EVENT_STRUCT.size:
                continue
            _sec, _usec, event_type, code, value = INPUT_EVENT_STRUCT.unpack(raw_event)

            if event_type != EV_KEY or code != BTN_TOUCH or value != 1:
                continue

            now = time.monotonic()
            if now - last_touch_check < TOUCH_DEBOUNCE_SECONDS:
                continue
            last_touch_check = now

            try:
                mode = get_power_mode(env)
            except Exception as exc:
                logging.warning("Could not read Mutter PowerSaveMode: %s", exc)
                continue

            if mode != 3:
                logging.debug("Touch detected; PowerSaveMode=%s, no wake needed", mode)
                continue

            if now - last_wake < WAKE_COOLDOWN_SECONDS:
                logging.info("Touch detected while display off; wake suppressed by cooldown")
                continue

            logging.info("Touch detected while display off; sending KEY_WAKEUP")
            emit_key(wake_fd, 1)
            time.sleep(0.1)
            emit_key(wake_fd, 0)
            last_wake = time.monotonic()

    except (KeyboardInterrupt, SystemExit):
        logging.info("Stopping touchscreen wake helper")
    except Exception:
        logging.exception("Touchscreen wake helper failed")
        return 1
    finally:
        if wake_fd is not None:
            if wake_device_created:
                try:
                    fcntl.ioctl(wake_fd, UI_DEV_DESTROY)
                except OSError:
                    pass
            try:
                os.close(wake_fd)
            except OSError:
                pass
        if input_fd is not None:
            try:
                os.close(input_fd)
            except OSError:
                pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
