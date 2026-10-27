# Touchscreen Wake for GNOME on Linux

A small, event-driven helper that wakes a GNOME display when the touchscreen is tapped, without changing GNOME's screen-saver state.

**Tested setup:** ASUS T101HA, Fedora Linux 43, GNOME on Wayland, touchscreen named `SIS0457:00 0457:11ED`. On that machine, a tap wakes the display and GNOME's existing 60-second automatic blanking continues to work.

This project was tested on one device. Other devices and GNOME/Mutter versions may behave differently.

[繁體中文說明](README.zh-TW.md)

## How it works

1. Reads touchscreen input events directly from the Linux `evdev` device. It discovers the event node from the device name, so it does not assume the touchscreen will always be `/dev/input/event4`.
2. When a `BTN_TOUCH` press is received, asks Mutter's `org.gnome.Mutter.DisplayConfig` D-Bus interface for `PowerSaveMode`.
3. If Mutter reports mode `3` (display off), creates a temporary virtual input device through `/dev/uinput` and sends `KEY_WAKEUP` (press + release).
4. It does **not** call `org.gnome.ScreenSaver.SetActive false`. On the tested device, that call caused normal automatic blanking to stop until the screen-saver state was reactivated.

The helper blocks while waiting for input; it does not continually poll the touchscreen. It uses Python's standard library and `gdbus` and does not require `evtest`, `python-evdev`, or `ydotool`.

## Requirements

- Linux with `/dev/uinput` available.
- Python 3 and `gdbus`.
- A GNOME/Mutter session exposing `org.gnome.Mutter.DisplayConfig` on the session D-Bus.
- A touchscreen that emits `EV_KEY / BTN_TOUCH` events and has the expected device name, or a small configuration change to match your device.
- The logged-in desktop user must be allowed to read the touchscreen event node and write to `/dev/uinput`.

## Install on the tested Fedora/GNOME setup

Extract or clone this project, open a terminal in the project directory, and run as the regular desktop user (do not use `sudo` for the whole command):

```bash
./install.sh
```

The installer:

- Installs the helper to `~/.local/bin/touchscreen-wake`.
- Installs a udev rule granting the active local user's session access to the named touchscreen and `/dev/uinput` via `uaccess`.
- Reloads udev rules and writes a GNOME autostart entry under `~/.config/autostart/`.
- Does not install packages.

The autostart entry runs at the **next GNOME login**. For an immediate manual test, run:

```bash
~/.local/bin/touchscreen-wake
```

Stop a manually started foreground process with `Ctrl+C`. Logs are written to:

```text
~/.local/state/touchscreen-wake.log
```

## Verify device access

After logging into the local GNOME desktop, run this as the desktop user (without `sudo`):

```bash
python3 - <<'PY'
import glob
import os
from pathlib import Path

touch = None
for entry in sorted(glob.glob('/sys/class/input/event*')):
    try:
        name = Path(entry, 'device', 'name').read_text().strip()
    except OSError:
        continue
    if name == 'SIS0457:00 0457:11ED':
        touch = '/dev/input/' + Path(entry).name
        break
if touch is None:
    raise SystemExit('Touchscreen was not found. Check TOUCH_DEVICE_NAME in touchscreen-wake.py.')
for path, flags in ((touch, os.O_RDONLY | os.O_NONBLOCK), ('/dev/uinput', os.O_WRONLY | os.O_NONBLOCK)):
    fd = os.open(path, flags)
    os.close(fd)
    print('OK:', path)
PY
```

Both devices should print `OK`. If access is denied, check that you are logged into the local GNOME desktop session and that the udev rule matches the device name. The `uaccess` ACL is meant for the active local session; an SSH session by itself may not receive the same device access.

## Configure another touchscreen

The tested touchscreen name is defined by `TOUCH_DEVICE_NAME` in `touchscreen-wake.py` and in `udev/70-touchscreen-wake.rules`. Find the exact name with:

```bash
for f in /sys/class/input/event*/device/name; do printf '%s: ' "$f"; cat "$f"; done
```

If adapting the project, change the name in both places, then run `./install.sh` again. The wake behavior also depends on the device driver, Mutter version, display power state, and whether `KEY_WAKEUP` is honored.

## Uninstall

Run from the project directory as the regular desktop user:

```bash
./uninstall.sh
```

It stops the user's running helper when found, removes the autostart entry and installed program, removes this project's udev rule, and reloads udev. It keeps the log file and does not uninstall other packages.

## Troubleshooting

- **No `Ready` message / process exits:** inspect `~/.local/state/touchscreen-wake.log`.
- **`Permission denied`:** run the device-access check above without `sudo`; verify the udev rule and active local GNOME session.
- **Mutter D-Bus error:** make sure the helper is launched inside the GNOME user's session, not as root. The query used by the helper is a session-bus request.
- **Touch is detected but no wake:** check that `PowerSaveMode` reports `3` while the display is off and test `KEY_WAKEUP` independently on the target device. `KEY_WAKEUP` is not guaranteed to wake every hardware/desktop combination.
- **The screen wakes but will not blank again:** ensure no older test script calling `org.gnome.ScreenSaver.SetActive false` is still running. This project deliberately avoids that call.

## Security and privacy

The helper reads touch events and creates a virtual input device. It does not access the network or send data anywhere. The udev rule is specific to the named touchscreen plus `/dev/uinput`; it uses `uaccess` rather than adding the user to the broad `input` group. Review the code and permissions before running it on another system.

## References

- [Linux kernel: uinput module](https://docs.kernel.org/input/uinput.html)
- [Linux kernel: input event codes (`KEY_WAKEUP`)](https://docs.kernel.org/input/event-codes.html)
- [GNOME: autostart applications](https://help.gnome.org/system-admin-guide/autostart-applications.html)

## License

MIT. See [LICENSE](LICENSE).
