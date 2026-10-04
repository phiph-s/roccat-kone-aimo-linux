#!/usr/bin/env python3
"""Sichert Report 6 (Einstellungen) und Report 7 (Tasten) aller 5 Profile (nur lesend)."""
import json, sys, time
sys.path.insert(0, 'src')
from aimo.device import KoneAimo, REPORT_STATUS, REPORT_PROFILE_SEL, REPORT_SETTINGS, REPORT_BUTTONS, SETTINGS_LEN, BUTTONS_LEN, checksum

out = {'device': '1e7d:2e2c', 'created': time.strftime('%Y-%m-%d %H:%M:%S'), 'profiles': {}}
with KoneAimo() as m:
    active = m.get_feature(REPORT_PROFILE_SEL, 3)
    out['active_profile_report5'] = active.hex()
    for p in range(5):
        m.set_feature(bytes([REPORT_STATUS, p, 0x80])); m.wait_ready()
        r6 = m.get_feature(REPORT_SETTINGS, SETTINGS_LEN)
        m.set_feature(bytes([REPORT_STATUS, p, 0x90])); m.wait_ready()
        r7 = m.get_feature(REPORT_BUTTONS, BUTTONS_LEN)
        ok = checksum(r6) == int.from_bytes(r6[-2:], 'little')
        print(f'Profil {p}: r6 {len(r6)}B (Checksumme {"ok" if ok else "FALSCH"}), r7 {len(r7)}B, r6[2]={r6[2]}')
        out['profiles'][p] = {'report6': r6.hex(), 'report7': r7.hex()}
fn = f'backups/profiles-{time.strftime("%Y%m%d-%H%M%S")}.json'
json.dump(out, open(fn, 'w'), indent=1)
print('Gespeichert:', fn)
