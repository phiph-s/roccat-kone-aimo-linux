#!/usr/bin/env python3
"""Schreibtest Profil 1: Slot 8 (Side back) -> Ctrl+Shift+T, zurücklesen, Original wiederherstellen."""
import sys
sys.path.insert(0, 'src')
from aimo.device import KoneAimo
from aimo.buttons import SHORTCUT, shortcut_label

with KoneAimo() as m:
    orig = bytes(m.read_buttons(0).raw)
    try:
        b = m.read_buttons(0)
        b.set_action(8, SHORTCUT, (0x01 | 0x02, 23))  # Ctrl+Shift, HID-Usage 23 = T
        m.write_buttons(0, b)
        back = m.read_buttons(0)
        print('Slot 8:', back.action(8), shortcut_label(*back.shortcut(8)))
        print('geänderte Offsets:', [i for i, (a, c) in enumerate(zip(orig, back.raw)) if a != c])
    finally:
        b = m.read_buttons(0); b.raw[:] = orig
        m.write_buttons(0, b)
        print('restored identical:', bytes(m.read_buttons(0).raw) == orig)
