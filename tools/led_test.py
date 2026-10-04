#!/usr/bin/env python3
import sys, time
sys.path.insert(0, 'src')
from aimo.device import KoneAimo, LED_COUNT

with KoneAimo() as m:
    s = m.read_settings()
    print('DPI', s.dpi(), 'aktiv', s.active_dpi_stage, 'Polling', s.polling_hz)
    m.direct_mode(True)
    for c in [(255, 0, 0), (0, 255, 0), (0, 0, 255)]:
        m.set_leds([c] * LED_COUNT); time.sleep(2.0)
    for i in range(LED_COUNT):  # Lauflicht
        m.set_leds([(255, 255, 255) if j == i else (0, 0, 0) for j in range(LED_COUNT)]); time.sleep(0.5)
    m.direct_mode(False)
    print('Direktmodus beendet')
