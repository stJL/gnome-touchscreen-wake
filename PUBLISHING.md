# Publish this project on GitHub

This folder is prepared for a new GitHub repository. Do not pre-create a README, license, or `.gitignore` in GitHub if you will push this whole local project, because those files are already included here.

## Suggested repository details

- Name: `gnome-touchscreen-wake`
- Description: `Event-driven touchscreen wake helper for GNOME on Linux, using evdev and uinput. Tested on ASUS T101HA / Fedora 43.`
- Visibility: Public, if you are comfortable sharing the code and device details.
- Default branch: `main`

## Publish from a terminal

1. Create an **empty** repository on GitHub. Do not tick options to add a README, a license, or `.gitignore` because this project already has those files.
2. Open a terminal in this project directory and run:

```bash
git init -b main
git add README.md README.zh-TW.md LICENSE CHANGELOG.md .gitignore PUBLISHING.md touchscreen-wake.py install.sh uninstall.sh udev/ autostart/
git commit -m "Initial release: touchscreen wake helper"
git remote add origin https://github.com/YOUR-USERNAME/gnome-touchscreen-wake.git
git push -u origin main
```

Replace `YOUR-USERNAME` with your GitHub username. Git may ask you to configure `user.name` and `user.email` before committing. Use the identity you want associated with your public commits. Do not put a password or access token into the remote URL.

If Git is not installed, install it using your distribution's package manager before following these steps. GitHub's documentation also explains creating an empty repository and pushing an existing local project.

## Keep a backup

Once published, clone a backup with:

```bash
git clone https://github.com/YOUR-USERNAME/gnome-touchscreen-wake.git
```

A public GitHub repository is a useful remote copy, but it is still wise to keep a local archive too:

```bash
cd ..
zip -r gnome-touchscreen-wake-backup.zip gnome-touchscreen-wake
```
