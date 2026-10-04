#!/usr/bin/env python3
"""Schreibtest an Profil 0: DPI-Stufe 5 von 3200 auf 3150 ändern, zurücklesen, Original wiederherstellen."""
import sys
sys.path.insert(0, 'src')
from aimo.device import KoneAimo

with KoneAimo() as m:
    orig = m.read_settings(0)
    orig_bytes = bytes(orig.raw)
    try:
        s = m.read_settings(0)
        d = s.dpi('x'); d[4] = 3150
        s.set_dpi(d)
        m.write_settings(s)
        back = m.read_settings(0)
        print('nach Schreiben  x:', back.dpi('x'), ' y:', back.dpi('y'))
        diff = [i for i, (a, b) in enumerate(zip(orig_bytes, back.raw)) if a != b]
        print('geänderte Offsets:', diff)
    finally:
        m.write_settings(type(orig)(bytearray(orig_bytes)))
        final = m.read_settings(0)
        print('nach Restore    x:', final.dpi('x'), ' identisch mit Original:', bytes(final.raw) == orig_bytes)
