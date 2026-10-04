"""Backend für die ROCCAT Kone Aimo (Remastered / 16K, USB 1e7d:2e2c) über hidraw."""
import fcntl
import glob
import os
import time
from dataclasses import dataclass, field

VID, PID = 0x1E7D, 0x2E2C

REPORT_STATUS, REPORT_PROFILE_SEL, REPORT_SETTINGS, REPORT_BUTTONS = 0x04, 0x05, 0x06, 0x07
REPORT_ACTIVATE, REPORT_DIRECT = 0x0E, 0x0D
SETTINGS_LEN, BUTTONS_LEN = 126, 75
LED_COUNT = 11  # 0 Rad, 1-4 links, 5-8 rechts, 9 unten links, 10 unten rechts


# Zone -> Offsets der {Intensität, R, G, B, 0}-Slots in Report 6
LED_ZONES = {
    'wheel': [61],
    'left': [66 + 5 * i for i in range(4)],
    'right': [86 + 5 * i for i in range(4)],
    'bottom': [106, 111],
}


def _ioc(direction, nr, size):
    return (direction << 30) | (size << 16) | (ord('H') << 8) | nr


def _hidiocsfeature(n): return _ioc(3, 0x06, n)
def _hidiocgfeature(n): return _ioc(3, 0x07, n)


class DeviceNotFound(Exception):
    pass


def find_node():
    """Control-Interface (Interface 0) der Maus finden."""
    for p in sorted(glob.glob('/sys/class/hidraw/hidraw*')):
        with open(p + '/device/uevent') as f:
            uevent = f.read()
        if f'HID_ID=0003:0000{VID:04X}:0000{PID:04X}' in uevent \
                and ':1.0/' in os.path.realpath(p + '/device') + '/':
            return '/dev/' + os.path.basename(p)
    raise DeviceNotFound('ROCCAT Kone Aimo nicht gefunden')


def checksum(data):
    """16-Bit-Byte-Summe über alles außer den letzten zwei Bytes."""
    return sum(data[:-2]) & 0xFFFF


@dataclass
class Settings:
    """Report 6 (126 Byte). Unbekannte Bytes bleiben beim Schreiben unverändert (raw)."""
    raw: bytearray = field(repr=False)

    @property
    def profile(self): return self.raw[2]

    @property
    def active_dpi_stage(self): return self.raw[5]

    @active_dpi_stage.setter
    def active_dpi_stage(self, v): self.raw[5] = v

    def dpi(self, axis='x'):
        base = 6 if axis == 'x' else 16
        return [int.from_bytes(self.raw[base + 2 * i:base + 2 * i + 2], 'little') * 50 for i in range(5)]

    def set_dpi(self, stages, axis='both'):
        for ax, base in (('x', 6), ('y', 16)):
            if axis in (ax, 'both'):
                for i, v in enumerate(stages):
                    self.raw[base + 2 * i:base + 2 * i + 2] = (v // 50).to_bytes(2, 'little')

    @property
    def polling_hz(self): return (125, 250, 500, 1000)[self.raw[26]]

    @polling_hz.setter
    def polling_hz(self, hz): self.raw[26] = (125, 250, 500, 1000).index(hz)

    # Effekt: 0 aus, 1 fest, 2 blinkend, 3 atmend, 4 Herzschlag, 7 Welle
    @property
    def effect(self): return self.raw[33]

    @effect.setter
    def effect(self, v): self.raw[33] = v

    @property
    def effect_speed(self): return self.raw[34]

    @effect_speed.setter
    def effect_speed(self, v): self.raw[34] = v

    @property
    def brightness(self): return self.raw[35]

    @brightness.setter
    def brightness(self, v): self.raw[35] = v

    def led_color(self, zone):
        """Farbe einer Zone (Name aus LED_ZONES) als (r, g, b)."""
        o = LED_ZONES[zone][0]
        return tuple(self.raw[o + 1:o + 4])

    def set_led_color(self, zone, rgb):
        for o in LED_ZONES[zone]:
            self.raw[o:o + 5] = bytes([0xFF, *rgb, 0x00])

    def finalize(self):
        self.raw[124:126] = checksum(self.raw).to_bytes(2, 'little')
        return bytes(self.raw)


class KoneAimo:
    def __init__(self, node=None):
        self.node = node or find_node()
        self.fd = os.open(self.node, os.O_RDWR)

    def close(self):
        os.close(self.fd)

    def __enter__(self): return self
    def __exit__(self, *a): self.close()

    def get_feature(self, report_id, length):
        buf = bytearray(length)
        buf[0] = report_id
        n = fcntl.ioctl(self.fd, _hidiocgfeature(length), buf)
        return bytes(buf[:n])

    def set_feature(self, data):
        fcntl.ioctl(self.fd, _hidiocsfeature(len(data)), bytes(data))

    def wait_ready(self, timeout=1.0):
        end = time.monotonic() + timeout
        while time.monotonic() < end:
            if self.get_feature(REPORT_STATUS, 3)[1] != 3:
                return
            time.sleep(0.1)

    # --- Profil / Einstellungen -------------------------------------------------
    def read_settings(self, profile=None):
        if profile is not None:
            self.set_feature(bytes([REPORT_STATUS, profile, 0x80]))
            self.wait_ready()
        return Settings(bytearray(self.get_feature(REPORT_SETTINGS, SETTINGS_LEN)))

    # --- LED-Direktmodus (nicht persistent) ------------------------------------
    def direct_mode(self, enable=True):
        self.get_feature(REPORT_STATUS, 3)
        self.set_feature(bytes([REPORT_ACTIVATE, 0x06, 0x01, 1 if enable else 0, 0x00, 0xFF]))

    def set_leds(self, colors):
        """colors: Liste aus 11 (r, g, b)-Tupeln."""
        assert len(colors) == LED_COUNT
        data = bytearray([REPORT_DIRECT, 0x2E])
        for r, g, b in colors:
            data += bytes([r, g, b, 0])
        self.set_feature(data)
        self.get_feature(REPORT_STATUS, 3)

    def write_settings(self, settings):
        """Report 6 in das Profil schreiben, das in settings.profile steht, und aktivieren."""
        data = settings.finalize()
        self.set_feature(bytes([REPORT_STATUS, settings.profile, 0x80]))
        self.wait_ready()
        self.set_feature(data)
        self.wait_ready()
        self.set_feature(bytes([REPORT_ACTIVATE, REPORT_SETTINGS, 0x01, 0x00, 0x00, 0xFF]))
        self.wait_ready()

    def active_profile(self):
        return self.get_feature(REPORT_PROFILE_SEL, 3)[2]

    def set_active_profile(self, profile):
        self.set_feature(bytes([REPORT_PROFILE_SEL, 0x03, profile]))
        self.wait_ready()

    # --- Tastenbelegung (Report 7, ohne Checksumme) ----------------------------
    def read_buttons(self, profile):
        from .buttons import Buttons
        self.set_feature(bytes([REPORT_STATUS, profile, 0x90]))
        self.wait_ready()
        return Buttons(bytearray(self.get_feature(REPORT_BUTTONS, BUTTONS_LEN)))

    def write_buttons(self, profile, buttons):
        self.set_feature(bytes([REPORT_STATUS, profile, 0x90]))
        self.wait_ready()
        data = bytearray(buttons.raw)
        data[2] = profile
        self.set_feature(data)
        self.wait_ready()
        self.set_feature(bytes([REPORT_ACTIVATE, REPORT_BUTTONS, 0x01, 0x00, 0x00, 0xFF]))
        self.wait_ready()
