"""GTK4/libadwaita-Oberfläche für die ROCCAT Kone Aimo."""
import sys

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Adw, Gdk, Gio, GLib, Gtk

from .buttons import (ACTIONS, EVDEV_MODIFIERS, EVDEV_TO_HID, SHORTCUT, SLOT_NAMES, SLOTS, WHEEL_SLOTS,
                      shortcut_label)
from .device import DeviceNotFound, KoneAimo, LED_ZONES

APP_ID = 'io.github.phiph.KoneAimo'
EFFECTS = [(1, 'Static'), (2, 'Blinking'), (3, 'Breathing'), (4, 'Heartbeat'), (7, 'Wave')]
POLLING = [125, 250, 500, 1000]
ZONE_NAMES = {'wheel': 'Scroll wheel', 'left': 'Left side', 'right': 'Right side', 'bottom': 'Underglow'}
BRIGHTNESS_MAX = 255


def to_rgba(rgb):
    c = Gdk.RGBA()
    c.red, c.green, c.blue, c.alpha = rgb[0] / 255, rgb[1] / 255, rgb[2] / 255, 1.0
    return c


def from_rgba(c):
    return tuple(round(v * 255) for v in (c.red, c.green, c.blue))


class MainWindow(Adw.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app, title='Kone Aimo', default_width=720, default_height=720)
        self.settings = None
        self.active = 0
        self.loading = False
        self.speed_loaded = None
        self.buttons = None
        self.buttons_loaded = None
        self.slot_rows = {}

        action = Gio.SimpleAction.new('make-active', None)
        action.connect('activate', lambda *_: self.make_active())
        self.add_action(action)
        self.make_active_action = action

        self.toasts = Adw.ToastOverlay()
        self.set_content(self.toasts)
        self.stack = Gtk.Stack()
        self.toasts.set_child(self.stack)
        self.stack.add_named(self._build_missing(), 'missing')
        self.stack.add_named(self._build_main(), 'main')
        self.reload()

    # --- Layout ---------------------------------------------------------------
    def _build_missing(self):
        page = Adw.StatusPage(icon_name='input-mouse-symbolic', title='No Mouse Found',
                              description='Connect your ROCCAT Kone Aimo and make sure the udev rule is installed.')
        retry = Gtk.Button(label='Try Again', halign=Gtk.Align.CENTER)
        retry.add_css_class('pill')
        retry.connect('clicked', lambda *_: self.reload())
        page.set_child(retry)
        view = Adw.ToolbarView()
        view.add_top_bar(Adw.HeaderBar())
        view.set_content(page)
        return view

    def _build_main(self):
        view = Adw.ToolbarView()
        header = Adw.HeaderBar()

        refresh = Gtk.Button(icon_name='view-refresh-symbolic', tooltip_text='Reload from mouse')
        refresh.connect('clicked', lambda *_: self.reload(self.settings.profile if self.settings else None, toast=True))
        header.pack_start(refresh)

        self.profile_drop = Gtk.DropDown(model=Gtk.StringList.new([]))
        self.profile_drop.connect('notify::selected', self._on_profile_changed)
        header.set_title_widget(self.profile_drop)

        apply_btn = Gtk.Button(label='Apply')
        apply_btn.add_css_class('suggested-action')
        apply_btn.connect('clicked', lambda *_: self.apply())
        header.pack_end(apply_btn)
        menu = Gio.Menu()
        menu.append('Use This Profile on Mouse', 'win.make-active')
        header.pack_end(Gtk.MenuButton(icon_name='open-menu-symbolic', menu_model=menu))
        view.add_top_bar(header)

        self.pages = Adw.ViewStack()
        self.pages.add_titled_with_icon(self._build_performance_page(), 'perf', 'Performance', 'power-profile-performance-symbolic')
        self.pages.add_titled_with_icon(self._build_lighting_page(), 'light', 'Lighting', 'weather-clear-symbolic')
        self.pages.add_titled_with_icon(self._build_buttons_page(), 'buttons', 'Buttons', 'input-mouse-symbolic')
        view.set_content(self.pages)
        view.add_bottom_bar(Adw.ViewSwitcherBar(stack=self.pages, reveal=True))
        return view

    def _build_performance_page(self):
        page = Adw.PreferencesPage()
        g = Adw.PreferencesGroup(title='DPI Stages')
        self.dpi_rows = []
        for i in range(5):
            r = Adw.SpinRow.new_with_range(100, 16000, 50)
            r.set_title(f'Stage {i + 1}')
            g.add(r)
            self.dpi_rows.append(r)
        page.add(g)

        g = Adw.PreferencesGroup()
        self.stage_row = Adw.ComboRow(title='Active Stage', model=Gtk.StringList.new([f'Stage {i + 1}' for i in range(5)]))
        g.add(self.stage_row)
        self.poll_row = Adw.ComboRow(title='Polling Rate', model=Gtk.StringList.new([f'{p} Hz' for p in POLLING]))
        g.add(self.poll_row)
        page.add(g)
        return page

    def _build_lighting_page(self):
        page = Adw.PreferencesPage()
        g = Adw.PreferencesGroup()
        self.effect_row = Adw.ComboRow(title='Effect', model=Gtk.StringList.new([n for _, n in EFFECTS]))
        self.effect_row.connect('notify::selected', self._update_speed_visibility)
        g.add(self.effect_row)
        self.speed_row = Adw.SpinRow.new_with_range(1, 3, 1)
        self.speed_row.set_title('Speed')
        g.add(self.speed_row)
        bright = Adw.ActionRow(title='Brightness')
        self.bright_scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 100, 1)
        self.bright_scale.set_hexpand(True)
        self.bright_scale.set_size_request(200, -1)
        self.bright_scale.set_valign(Gtk.Align.CENTER)
        self.bright_scale.set_draw_value(True)
        self.bright_scale.set_value_pos(Gtk.PositionType.LEFT)
        self.bright_scale.set_format_value_func(lambda _s, v: f'{v:.0f}%')
        bright.add_suffix(self.bright_scale)
        g.add(bright)
        page.add(g)

        g = Adw.PreferencesGroup(title='Colors')
        self.color_btns = {}
        for zone, name in ZONE_NAMES.items():
            row = Adw.ActionRow(title=name)
            btn = Gtk.ColorDialogButton(dialog=Gtk.ColorDialog(with_alpha=False), valign=Gtk.Align.CENTER)
            row.add_suffix(btn)
            g.add(row)
            self.color_btns[zone] = btn
        page.add(g)
        return page

    def _build_buttons_page(self):
        page = Adw.PreferencesPage()
        for layer, title, desc in ((0, 'Buttons', None),
                                   (SLOTS, 'Easy-Shift Layer', 'Active while the Easy-Shift button is held.')):
            g = Adw.PreferencesGroup(title=title, description=desc)
            for i in range(SLOTS):
                slot = layer + i
                if slot == SLOTS + 9:  # Easy-Shift-Taste selbst hat keine zweite Ebene
                    continue
                row = Adw.ComboRow(title=SLOT_NAMES[i])
                combo_model = Gtk.StringList.new([n for _, n in self._actions_for(slot)])
                row.set_model(combo_model)
                key_btn = Gtk.Button(valign=Gtk.Align.CENTER)
                key_btn.add_css_class('flat')
                key_btn.connect('clicked', lambda _b, sl=slot: self._record_shortcut(sl))
                row.add_suffix(key_btn)
                row.connect('notify::selected', lambda r, _p, sl=slot: self._on_action_selected(sl))
                g.add(row)
                self.slot_rows[slot] = (row, key_btn)
            page.add(g)
        return page

    @staticmethod
    def _actions_for(slot):
        # Scrollrad-Slots dürfen nicht deaktiviert werden (sonst scrollt die Maus nicht mehr)
        return [(c, n) for c, n in ACTIONS if not (c == 0 and slot % SLOTS in WHEEL_SLOTS)]

    def _sync_slot(self, slot):
        row, key_btn = self.slot_rows[slot]
        action = self.buttons.action(slot)
        codes = [c for c, _ in self._actions_for(slot)]
        row.set_selected(codes.index(action) if action in codes else 0)
        is_sc = action == SHORTCUT
        key_btn.set_visible(is_sc)
        if is_sc:
            key_btn.set_label(shortcut_label(*self.buttons.shortcut(slot)))

    def _on_action_selected(self, slot):
        if self.loading or self.buttons is None:
            return
        row, _ = self.slot_rows[slot]
        code = self._actions_for(slot)[row.get_selected()][0]
        if code == SHORTCUT:
            if self.buttons.action(slot) != SHORTCUT:
                self._record_shortcut(slot)
            return
        self.buttons.set_action(slot, code)
        self._sync_slot(slot)

    def _record_shortcut(self, slot):
        dialog = Adw.Dialog(title='Record Shortcut', content_width=360)
        status = Adw.StatusPage(icon_name='input-keyboard-symbolic', title='Press a key combination',
                                description='Hold modifiers such as Ctrl or Shift, then press a key.')
        cancel = Gtk.Button(label='Cancel', halign=Gtk.Align.CENTER)
        cancel.add_css_class('pill')
        cancel.connect('clicked', lambda *_: dialog.close())
        status.set_child(cancel)
        dialog.set_child(status)

        held = {}
        ctrl = Gtk.EventControllerKey()
        ctrl.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)

        def pressed(_c, _keyval, keycode, _state):
            evdev = keycode - 8  # GDK-Hardware-Keycode = evdev + 8
            if evdev in EVDEV_MODIFIERS:
                held[evdev] = EVDEV_MODIFIERS[evdev]
                return True
            usage = EVDEV_TO_HID.get(evdev)
            if usage is None:
                self.toast('This key is not supported')
                return True
            mods = 0
            for bit in held.values():
                mods |= bit
            self.buttons.set_action(slot, SHORTCUT, (mods, usage))
            self.loading = True
            self._sync_slot(slot)
            self.loading = False
            dialog.close()
            return True

        ctrl.connect('key-pressed', pressed)
        ctrl.connect('key-released', lambda _c, _k, kc, _s: held.pop(kc - 8, None))
        dialog.add_controller(ctrl)
        dialog.connect('closed', lambda *_: self._sync_slot(slot))
        dialog.present(self)

    def _update_speed_visibility(self, *_):
        self.speed_row.set_visible(EFFECTS[self.effect_row.get_selected()][0] != 1)

    # --- Device ---------------------------------------------------------------
    def toast(self, text):
        self.toasts.add_toast(Adw.Toast(title=text, timeout=2))

    def _refresh_profile_labels(self):
        labels = [f'Profile {i + 1}' + ('  ·  on mouse' if i == self.active else '') for i in range(5)]
        sel = self.profile_drop.get_selected()
        self.profile_drop.set_model(Gtk.StringList.new(labels))
        self.profile_drop.set_selected(self.settings.profile if self.settings else sel)

    def reload(self, profile=None, toast=False):
        try:
            with KoneAimo() as m:
                self.active = m.active_profile()
                self.settings = m.read_settings(self.active if profile is None else profile)
                self.buttons = m.read_buttons(self.settings.profile)
                self.buttons_loaded = bytes(self.buttons.raw)
        except (DeviceNotFound, OSError):
            self.stack.set_visible_child_name('missing')
            return
        s = self.settings
        self.loading = True
        self._refresh_profile_labels()
        for r, v in zip(self.dpi_rows, s.dpi('x')):
            r.set_value(v)
        self.stage_row.set_selected(s.active_dpi_stage)
        self.poll_row.set_selected(POLLING.index(s.polling_hz))
        ids = [i for i, _ in EFFECTS]
        self.effect_row.set_selected(ids.index(s.effect) if s.effect in ids else 0)
        self.speed_loaded = min(max(s.effect_speed, 1), 3)
        self.speed_row.set_value(self.speed_loaded)
        self.bright_scale.set_value(round(s.brightness * 100 / BRIGHTNESS_MAX))
        for zone, btn in self.color_btns.items():
            btn.set_rgba(to_rgba(s.led_color(zone)))
        for slot in self.slot_rows:
            self._sync_slot(slot)
        self._update_speed_visibility()
        self.make_active_action.set_enabled(s.profile != self.active)
        self.loading = False
        self.stack.set_visible_child_name('main')
        if toast:
            self.toast('Reloaded from mouse')

    def _on_profile_changed(self, drop, _):
        if self.loading or self.settings is None or drop.get_selected() == self.settings.profile:
            return
        self.reload(drop.get_selected())

    def make_active(self):
        try:
            with KoneAimo() as m:
                m.set_active_profile(self.settings.profile)
            self.active = self.settings.profile
            self.loading = True
            self._refresh_profile_labels()
            self.loading = False
            self.make_active_action.set_enabled(False)
            self.toast(f'Profile {self.active + 1} is now active on the mouse')
        except Exception as e:
            self.toast(f'Error: {e}')

    def apply(self):
        if bytes(self.buttons.raw) != self.buttons_loaded and \
                not any(self.buttons.action(i) == 1 for i in range(SLOTS)):
            dlg = Adw.AlertDialog(heading='No Left Click Assigned',
                                  body='No button is set to Left Click. You may not be able to click anymore.')
            dlg.add_response('cancel', 'Cancel')
            dlg.add_response('apply', 'Apply Anyway')
            dlg.set_response_appearance('apply', Adw.ResponseAppearance.DESTRUCTIVE)
            dlg.connect('response', lambda _d, r: self._write() if r == 'apply' else None)
            dlg.present(self)
            return
        self._write()

    def _write(self):
        s = self.settings
        s.set_dpi([int(r.get_value()) for r in self.dpi_rows])
        s.active_dpi_stage = self.stage_row.get_selected()
        s.polling_hz = POLLING[self.poll_row.get_selected()]
        s.effect = EFFECTS[self.effect_row.get_selected()][0]
        if int(self.speed_row.get_value()) != self.speed_loaded:  # unbekannte Skala: nur bei Änderung schreiben
            s.effect_speed = int(self.speed_row.get_value())
        s.brightness = round(self.bright_scale.get_value() * BRIGHTNESS_MAX / 100)
        for zone, btn in self.color_btns.items():
            s.set_led_color(zone, from_rgba(btn.get_rgba()))
        try:
            with KoneAimo() as m:
                m.write_settings(s)
                if bytes(self.buttons.raw) != self.buttons_loaded:
                    m.write_buttons(s.profile, self.buttons)
                    self.buttons_loaded = bytes(self.buttons.raw)
            self.toast(f'Profile {s.profile + 1} saved')
        except Exception as e:
            self.toast(f'Error: {e}')


class App(Adw.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID, flags=Gio.ApplicationFlags.DEFAULT_FLAGS)

    def do_activate(self):
        (self.props.active_window or MainWindow(self)).present()


def main():
    return App().run(sys.argv)
