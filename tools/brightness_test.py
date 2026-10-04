#!/usr/bin/env python3
import sys, time
sys.path.insert(0, 'src')
from aimo.device import KoneAimo

with KoneAimo() as m:
    orig = bytes(m.read_settings(0).raw)
    try:
        for v in (12, 60, 130, 255, 0):
            s = m.read_settings(0); s.brightness = v
            m.write_settings(s)
            print('Helligkeit', v, flush=True)
            time.sleep(3)
    finally:
        s = m.read_settings(0); s.raw[:] = orig
        m.write_settings(s)
        print('restored identical:', bytes(m.read_settings(0).raw) == orig)
