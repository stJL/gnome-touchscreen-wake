#!/usr/bin/env bash
set -euo pipefail

if [[ "${EUID}" -eq 0 ]]; then
  echo "Please run this installer as your regular desktop user, not with sudo." >&2
  exit 1
fi

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROGRAM_NAME="touchscreen-wake"
INSTALL_DIR="${HOME}/.local/bin"
PROGRAM_PATH="${INSTALL_DIR}/${PROGRAM_NAME}"
AUTOSTART_DIR="${HOME}/.config/autostart"
AUTOSTART_PATH="${AUTOSTART_DIR}/${PROGRAM_NAME}.desktop"
UDEV_RULE="${SCRIPT_DIR}/udev/70-touchscreen-wake.rules"

for cmd in python3 gdbus sudo udevadm; do
  if ! command -v "${cmd}" >/dev/null 2>&1; then
    echo "Missing required command: ${cmd}" >&2
    exit 1
  fi
done

if [[ ! -r "${SCRIPT_DIR}/touchscreen-wake.py" || ! -r "${UDEV_RULE}" ]]; then
  echo "Run this installer from the extracted project directory; required files are missing." >&2
  exit 1
fi

# Ask for privilege once before copying the system-wide udev rule.
sudo -v
install -Dm755 "${SCRIPT_DIR}/touchscreen-wake.py" "${PROGRAM_PATH}"
sudo install -Dm644 "${UDEV_RULE}" /etc/udev/rules.d/70-touchscreen-wake.rules

sudo udevadm control --reload-rules
# Re-evaluate input-device access tags, then the uinput node.
sudo udevadm trigger --action=change --subsystem-match=input
sudo udevadm trigger --action=change --subsystem-match=misc --sysname-match=uinput

mkdir -p "${AUTOSTART_DIR}"
exec_path="${PROGRAM_PATH//\\/\\\\}"
exec_path="${exec_path//\"/\\\"}"
sed "s|@EXEC_PATH@|${exec_path}|g" \
  "${SCRIPT_DIR}/autostart/touchscreen-wake.desktop.in" > "${AUTOSTART_PATH}"
chmod 644 "${AUTOSTART_PATH}"

printf '\nInstallation files created:\n  Program:   %s\n  Autostart: %s\n  Udev rule: %s\n' \
  "${PROGRAM_PATH}" "${AUTOSTART_PATH}" "/etc/udev/rules.d/70-touchscreen-wake.rules"
printf '\nThe helper will start automatically at the next GNOME login.\n'
printf 'For an immediate manual test, run: %s\n' "${PROGRAM_PATH}"
printf 'Log file: %s/.local/state/touchscreen-wake.log\n' "${HOME}"
printf '\nIf device access is denied, confirm you are logged into the local GNOME desktop session, then re-check the troubleshooting section in README.md.\n'
