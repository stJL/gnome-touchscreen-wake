# Changelog

## 0.1.0 — 2026-10-28

- Initial public-ready release based on the version tested on ASUS T101HA / Fedora 43 / GNOME Wayland.
- Detects touch input by touchscreen name rather than hard-coded event number.
- Sends `KEY_WAKEUP` through a temporary `uinput` device only while Mutter reports the display off.
- Adds install and uninstall scripts, a udev rule, GNOME autostart entry template, and English/Traditional Chinese documentation.
