#!/usr/bin/env bash
# Installiert Kone Aimo für den aktuellen Benutzer (~/.local). Nur die udev-Regel braucht sudo.
#   ./install.sh               installieren
#   ./install.sh --uninstall   entfernen
#   PREFIX=/pfad ./install.sh  anderes Ziel (z. B. zum Testen), udev-Regel wird dann übersprungen
set -euo pipefail
cd "$(dirname "$0")"

APP_ID=io.github.phiph.KoneAimo
PREFIX="${PREFIX:-$HOME/.local}"
LIBDIR="$PREFIX/share/kone-aimo"
UDEV=/etc/udev/rules.d/70-roccat-kone-aimo.rules

refresh_caches() {
    command -v update-desktop-database >/dev/null && update-desktop-database "$PREFIX/share/applications" 2>/dev/null || true
    command -v gtk-update-icon-cache >/dev/null && gtk-update-icon-cache -qtf "$PREFIX/share/icons/hicolor" 2>/dev/null || true
}

if [[ "${1:-}" == "--uninstall" ]]; then
    rm -rf "$LIBDIR" "$PREFIX/bin/kone-aimo" \
        "$PREFIX/share/applications/$APP_ID.desktop" \
        "$PREFIX/share/icons/hicolor/scalable/apps/$APP_ID.svg" \
        "$PREFIX/share/metainfo/$APP_ID.metainfo.xml"
    refresh_caches
    echo "Entfernt. Die udev-Regel bleibt, entfernen mit: sudo rm $UDEV"
    exit 0
fi

python3 -c "import gi; gi.require_version('Gtk','4.0'); gi.require_version('Adw','1')" 2>/dev/null || {
    echo "Fehlt: PyGObject mit GTK4 und libadwaita (Arch: sudo pacman -S python-gobject gtk4 libadwaita)" >&2; exit 1; }

rm -rf "$LIBDIR"
install -d "$LIBDIR" "$PREFIX/bin" "$PREFIX/share/applications" \
    "$PREFIX/share/icons/hicolor/scalable/apps" "$PREFIX/share/metainfo"
cp -r src/aimo "$LIBDIR/"
find "$LIBDIR" -name __pycache__ -prune -exec rm -rf {} +
sed "s|@LIBDIR@|$LIBDIR|" bin/kone-aimo > "$PREFIX/bin/kone-aimo"
chmod 755 "$PREFIX/bin/kone-aimo"
sed "s|^Exec=.*|Exec=$PREFIX/bin/kone-aimo|" data/$APP_ID.desktop > "$PREFIX/share/applications/$APP_ID.desktop"
install -m644 data/$APP_ID.svg "$PREFIX/share/icons/hicolor/scalable/apps/"
install -m644 data/$APP_ID.metainfo.xml "$PREFIX/share/metainfo/"
refresh_caches
echo "Installiert nach $PREFIX"

if [[ "$PREFIX" == "$HOME/.local" ]]; then
    if cmp -s udev/70-roccat-kone-aimo.rules "$UDEV" 2>/dev/null; then
        echo "udev-Regel ist bereits installiert."
    else
        echo "Die Maus braucht eine udev-Regel, damit kein root nötig ist (sudo-Passwort wird abgefragt):"
        sudo install -m644 udev/70-roccat-kone-aimo.rules "$UDEV"
        sudo udevadm control --reload
        sudo udevadm trigger --subsystem-match=hidraw
    fi
fi
echo "Fertig. Starten über das Anwendungsmenü ('Kone Aimo') oder: kone-aimo"
