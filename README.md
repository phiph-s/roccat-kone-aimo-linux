# Kone Aimo for Linux

A small, native GNOME app (Python, GTK4 + libadwaita) to configure the **ROCCAT Kone Aimo** mouse
(Remastered / 16K, USB ID `1e7d:2e2c`) without the Windows software.

[roccat-tools](https://sourceforge.net/projects/roccat/) does not support this mouse, so the protocol was
worked out from [libratbag PR #1883](https://github.com/libratbag/libratbag/pull/1883), OpenRGB and other
community projects, and verified against a real Kone Aimo 16K.

## Features

- **Performance:** 5 DPI stages (100–16000), active stage, polling rate (125–1000 Hz)
- **Lighting:** effect (static, blinking, breathing, heartbeat, wave), speed, brightness, colors for wheel,
  left side, right side and underglow
- **Buttons:** reassign all 12 buttons and the 12 Easy-Shift layer slots: clicks, scrolling, DPI and profile
  switching, media keys and recorded keyboard shortcuts
- **Profiles:** edit any of the 5 on-mouse profiles and choose which one is active. Everything is stored in the
  mouse, so it keeps working without the app

Not supported yet: macros, restoring a backup from the UI.

## Install

Requires Python 3 with PyGObject, GTK 4 and libadwaita
(Arch: `sudo pacman -S python-gobject gtk4 libadwaita`).

    git clone git@github.com:phiph-s/roccat-kone-aimo-linux.git
    cd roccat-kone-aimo-linux
    ./install.sh

This installs the app for the current user into `~/.local` and, after asking for `sudo`, a udev rule that lets
your logged-in user access the mouse (`udev/70-roccat-kone-aimo.rules`). Then start **Kone Aimo** from the
application menu or run `kone-aimo`. Remove it with `./install.sh --uninstall`.

## Safety

The app writes to the mouse's flash. Before experimenting, save your profiles:

    python tools/backup.py

This writes all 5 profiles (settings and buttons) to `backups/` as JSON. Write operations are limited to
DPI/polling/lighting settings (Report 6) and button assignments (Report 7); no firmware commands are used.
The app asks for confirmation if you leave no button assigned to Left Click, and the four scroll-wheel slots
cannot be disabled (the firmware needs them for scrolling).

## Protocol notes

All communication uses HID feature reports on `hidraw` (interface 0):

| Report | Size | Purpose |
|---|---|---|
| `0x04` | 3 | select profile + data type (`0x80` settings, `0x90` buttons) / ready status |
| `0x05` | 3 | active profile |
| `0x06` | 126 | settings: DPI, polling, effect, brightness, LED colors, 16-bit byte-sum checksum (LE) |
| `0x07` | 75 | 24 button slots of `{action u8, modifiers u16}`, no checksum |
| `0x0e` | 6 | activate the data just written (`0e <report> 01 00 00 ff`) / enable direct LED mode |
| `0x0d` | 46 | direct LED colors (11 LEDs, `R G B 0`), not persistent |

See `src/aimo/device.py` and `src/aimo/buttons.py`. The scripts in `tools/` are small test helpers
(LED animations, write tests that restore the original data).

## Disclaimer

This is an unofficial, unaffiliated project. It was tested on one Kone Aimo 16K; other revisions
(e.g. the original Kone Aimo `1e7d:2e27`) may use different layouts. Use at your own risk.

## License

GPL-3.0-or-later, see [LICENSE](LICENSE).
