#!/usr/bin/env bash
set -euo pipefail

if [[ "${EUID}" -eq 0 ]]; then
  echo "Please run this uninstaller as your regular desktop user, not with sudo." >&2
  exit 1
fi

PROGRAM_PATH="${HOME}/.local/bin/touchscreen-wake"
AUTOSTART_PATH="${HOME}/.config/autostart/touchscreen-wake.desktop"
UDEV_PATH="/etc/udev/rules.d/70-touchscreen-wake.rules"

# Stop only Python processes whose script argument matches this user's installed helper.
python3 - "${PROGRAM_PATH}" <<'PY'
import os
import signal
import sys
import time

program = os.path.realpath(sys.argv[1])
current_pid = os.getpid()
matched = []
for entry in os.listdir('/proc'):
    if not entry.isdigit() or int(entry) in (current_pid, os.getppid()):
        continue
    try:
        with open(f'/proc/{entry}/cmdline', 'rb') as stream:
            raw = stream.read()
        args = [part.decode(errors='replace') for part in raw.split(b'\0') if part]
    except (OSError, ProcessLookupError):
        continue
    if len(args) >= 2 and os.path.realpath(args[1]) == program:
        try:
            os.kill(int(entry), signal.SIGTERM)
            matched.append(entry)
        except (OSError, ProcessLookupError):
            pass
if matched:
    time.sleep(0.3)
    print('Sent SIGTERM to helper PID(s): ' + ', '.join(matched))
else:
    print('No running touchscreen-wake process found for this user.')
PY

rm -f "${AUTOSTART_PATH}" "${PROGRAM_PATH}"
sudo -v
sudo rm -f "${UDEV_PATH}"
sudo udevadm control --reload-rules
sudo udevadm trigger --action=change --subsystem-match=input
sudo udevadm trigger --action=change --subsystem-match=misc --sysname-match=uinput

cat <<__UNINSTALL_MESSAGE__

Touchscreen Wake has been removed.
The log file was kept, if present:
  ${HOME}/.local/state/touchscreen-wake.log

No other packages were removed.
__UNINSTALL_MESSAGE__
