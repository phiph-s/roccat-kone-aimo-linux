#!/usr/bin/env python3
"""Liest (nur lesend!) alle Feature-Reports aus dem HID-Deskriptor der Kone Aimo und gibt sie als Hex aus."""
import fcntl, glob, os, struct, sys

VID, PID = 0x1E7D, 0x2E2C
# Report-ID -> Datenlänge (ohne ID-Byte), aus dem Report-Deskriptor von Interface 0
FEATURE_SIZES = {0x04: 2, 0x05: 3, 0x06: 125, 0x07: 74, 0x08: 260, 0x09: 8, 0x0A: 7,
                 0x0C: 3, 0x0D: 45, 0x0E: 5, 0x0F: 5, 0x10: 15, 0x11: 16, 0x12: 63,
                 0x1A: 1028, 0x1B: 260, 0x1C: 2}

def _ioc(d, t, nr, size): return (d << 30) | (size << 16) | (ord(t) << 8) | nr
def HIDIOCGFEATURE(n): return _ioc(3, 'H', 0x07, n)

def find_control_node():
    for p in sorted(glob.glob('/sys/class/hidraw/hidraw*')):
        uevent = open(p + '/device/uevent').read()
        if f'HID_ID=0003:0000{VID:04X}:0000{PID:04X}' in uevent and '.0/' in os.path.realpath(p + '/device') + '/':
            return '/dev/' + os.path.basename(p)
    sys.exit('Kone Aimo nicht gefunden')

def main():
    node = find_control_node()
    print('Gerät:', node)
    fd = os.open(node, os.O_RDWR)
    for rid, size in FEATURE_SIZES.items():
        buf = bytearray(size + 1); buf[0] = rid
        try:
            n = fcntl.ioctl(fd, HIDIOCGFEATURE(len(buf)), buf)
            print(f'\n[0x{rid:02x}] {n} Byte\n' + buf[:n].hex(' ', 1))
        except OSError as e:
            print(f'\n[0x{rid:02x}] Fehler: {e}')

if __name__ == '__main__':
    main()
