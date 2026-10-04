#!/usr/bin/env python3
"""Regenbogen, der über die 11 LEDs rotiert (Direktmodus, nicht persistent)."""
import colorsys, sys, time
sys.path.insert(0, 'src')
from aimo.device import KoneAimo, LED_COUNT

DURATION = float(sys.argv[1]) if len(sys.argv) > 1 else 8.0

with KoneAimo() as m:
    m.direct_mode(True)
    try:
        t0 = time.monotonic()
        while (t := time.monotonic() - t0) < DURATION:
            m.set_leds([tuple(int(c * 255) for c in colorsys.hsv_to_rgb((t * 0.5 + i / LED_COUNT) % 1, 1, 1))
                        for i in range(LED_COUNT)])
            time.sleep(0.03)
    finally:
        m.direct_mode(False)
