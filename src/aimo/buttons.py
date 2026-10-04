"""Tastenbelegung (Report 7): 24 Slots à {u8 Aktion, u16 Modifier/Taste}, 12 normal + 12 Easy Shift."""
from dataclasses import dataclass

SHORTCUT = 0x05
SLOTS = 12

# Aktionscode -> Anzeigename (Reihenfolge = Reihenfolge im Auswahlmenü)
ACTIONS = [
    (0, 'Disabled'),
    (1, 'Left Click'), (2, 'Right Click'), (3, 'Middle Click'), (4, 'Double Click'),
    (7, 'Browser Forward'), (8, 'Browser Back'),
    (13, 'Scroll Up'), (14, 'Scroll Down'), (9, 'Scroll Left'), (10, 'Scroll Right'),
    (20, 'DPI Cycle'), (21, 'DPI Up'), (22, 'DPI Down'),
    (16, 'Profile Cycle'), (17, 'Profile Up'), (18, 'Profile Down'),
    (35, 'Play / Pause'), (33, 'Previous Track'), (34, 'Next Track'), (36, 'Stop'),
    (37, 'Mute'), (38, 'Volume Up'), (39, 'Volume Down'),
    (65, 'Easy Shift'),
    (SHORTCUT, 'Keyboard Shortcut…'),
]
ACTION_NAMES = dict(ACTIONS)

SLOT_NAMES = ['Left button', 'Right button', 'Wheel click', 'Wheel tilt left', 'Wheel tilt right',
              'Wheel up', 'Wheel down', 'Side button forward', 'Side button back',
              'Easy-Shift button', 'Top button up', 'Top button down']
WHEEL_SLOTS = (3, 4, 5, 6)  # Aktion darf nicht 0 sein, sonst funktioniert das Scrollrad nicht

# HID-Usage -> Linux-evdev-Keycode (Umkehrung der Kernel-Tabelle hid_keyboard)
_EVDEV = {**{4 + i: c for i, c in enumerate([30, 48, 46, 32, 18, 33, 34, 35, 23, 36, 37, 38, 50, 49, 24,
                                              25, 16, 19, 31, 20, 22, 47, 17, 45, 21, 44])},
          **{30 + i: 2 + i for i in range(10)},
          40: 28, 41: 1, 42: 14, 43: 15, 44: 57, 45: 12, 46: 13, 47: 26, 48: 27, 49: 43, 51: 39, 52: 40,
          53: 41, 54: 51, 55: 52, 56: 53, 57: 58, 70: 99, 71: 70, 72: 119, 73: 110, 74: 102, 75: 104,
          76: 111, 77: 107, 78: 109, 79: 106, 80: 105, 81: 108, 82: 103, 100: 86,
          **{58 + i: c for i, c in enumerate([59, 60, 61, 62, 63, 64, 65, 66, 67, 68, 87, 88])}}
EVDEV_TO_HID = {v: k for k, v in _EVDEV.items()}

# evdev-Keycode der Modifier -> HID-Modifierbit
EVDEV_MODIFIERS = {29: 0x01, 42: 0x02, 56: 0x04, 125: 0x08, 97: 0x10, 54: 0x20, 100: 0x40, 126: 0x80}

_LABELS = {40: 'Enter', 41: 'Esc', 42: 'Backspace', 43: 'Tab', 44: 'Space', 45: '-', 46: '=', 47: '[', 48: ']',
           49: '\\', 51: ';', 52: "'", 53: '`', 54: ',', 55: '.', 56: '/', 57: 'Caps Lock', 70: 'Print',
           71: 'Scroll Lock', 72: 'Pause', 73: 'Insert', 74: 'Home', 75: 'Page Up', 76: 'Delete', 77: 'End',
           78: 'Page Down', 79: 'Right', 80: 'Left', 81: 'Down', 82: 'Up', 100: '<'}
_MOD_LABELS = [(0x01, 'Ctrl'), (0x10, 'Ctrl'), (0x02, 'Shift'), (0x20, 'Shift'), (0x04, 'Alt'), (0x40, 'AltGr'),
               (0x08, 'Super'), (0x80, 'Super')]


def key_label(usage):
    if 4 <= usage <= 29:
        return chr(ord('A') + usage - 4)
    if 30 <= usage <= 38:
        return str(usage - 29)
    if usage == 39:
        return '0'
    if 58 <= usage <= 69:
        return f'F{usage - 57}'
    return _LABELS.get(usage, f'Key 0x{usage:02x}')


def shortcut_label(mods, usage):
    parts = []
    for bit, name in _MOD_LABELS:
        if mods & bit and name not in parts:
            parts.append(name)
    parts.append(key_label(usage))
    return ' + '.join(parts)


@dataclass
class Buttons:
    raw: bytearray

    def action(self, slot):
        return self.raw[3 + 3 * slot]

    def shortcut(self, slot):
        """(hid_modifiers, hid_usage) eines Shortcut-Slots."""
        v = int.from_bytes(self.raw[4 + 3 * slot:6 + 3 * slot], 'little')
        return v & 0xFF, v >> 8

    def set_action(self, slot, action, shortcut=(0, 0)):
        self.raw[3 + 3 * slot] = action
        mods, usage = shortcut if action == SHORTCUT else (0, 0)
        self.raw[4 + 3 * slot:6 + 3 * slot] = (mods | usage << 8).to_bytes(2, 'little')
