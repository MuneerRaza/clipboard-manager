#!/usr/bin/python3
"""
Clipboard Manager UI for GNOME Wayland
Uses GPaste daemon as backend (event-driven, no polling)
Uses ydotool for auto-paste
"""

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Gdk', '4.0')
from gi.repository import Gtk, Gdk, Gio, GLib
import subprocess
import sys
import os

# Set ydotool socket path
os.environ['YDOTOOL_SOCKET'] = '/tmp/.ydotool_socket'


class GPasteClient:
    """Interface to GPaste daemon via CLI"""

    def get_history(self, limit=50):
        """Get clipboard history from GPaste"""
        try:
            result = subprocess.run(
                ['gpaste-client', '--oneline'],
                capture_output=True,
                text=True,
                timeout=2
            )
            if result.returncode != 0:
                return []

            entries = []
            lines = result.stdout.strip().split('\n')
            for i, line in enumerate(lines[:limit]):
                if ':' in line:
                    parts = line.split(':', 1)
                    if len(parts) == 2:
                        uuid = parts[0].strip()
                        content = parts[1].strip()
                        if content:
                            entries.append({'index': i, 'uuid': uuid, 'content': content})
            return entries
        except Exception:
            return []

    def select_item(self, index):
        """Select item from history by index (copies to clipboard)"""
        try:
            subprocess.run(
                ['gpaste-client', 'select', '--use-index', str(index)],
                capture_output=True,
                timeout=2
            )
        except Exception:
            pass

    def clear_history(self):
        """Clear all history"""
        try:
            subprocess.run(
                ['gpaste-client', 'empty'],
                capture_output=True,
                timeout=2
            )
        except Exception:
            pass


class ClipboardOverlay(Gtk.ApplicationWindow):
    """Overlay window - Windows-like clipboard popup"""

    def __init__(self, app):
        super().__init__(application=app)
        self.gpaste = GPasteClient()
        self.set_title("Clipboard Manager")
        self.set_default_size(520, 450)
        self.set_decorated(False)
        self.set_modal(True)

        self.build_ui()
        self.load_css()

        # Keyboard controller
        key_controller = Gtk.EventControllerKey()
        key_controller.connect("key-pressed", self.on_key_pressed)
        self.add_controller(key_controller)

        # Close on focus lost (click outside)
        focus_controller = Gtk.EventControllerFocus()
        focus_controller.connect("leave", self.on_focus_lost)
        self.add_controller(focus_controller)

    def on_focus_lost(self, controller):
        """Close when clicking outside"""
        self.close()

    def build_ui(self):
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        main_box.set_margin_top(20)
        main_box.set_margin_bottom(20)
        main_box.set_margin_start(20)
        main_box.set_margin_end(20)

        # Top row: Search + Clear
        top_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)

        self.search_entry = Gtk.SearchEntry()
        self.search_entry.set_placeholder_text("Search ...")
        self.search_entry.set_hexpand(True)
        self.search_entry.connect("search-changed", self.on_search_changed)
        self.search_entry.add_css_class("search-entry")
        top_row.append(self.search_entry)

        clear_btn = Gtk.Button(label="Clear")
        clear_btn.connect("clicked", self.on_clear_clicked)
        clear_btn.add_css_class("clear-button")
        top_row.append(clear_btn)

        main_box.append(top_row)

        # Scrolled list
        self.scrolled = Gtk.ScrolledWindow()
        self.scrolled.set_vexpand(True)
        self.scrolled.set_hexpand(True)
        self.scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        self.listbox = Gtk.ListBox()
        self.listbox.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.listbox.connect("row-activated", self.on_row_activated)
        self.listbox.add_css_class("clipboard-list")

        self.scrolled.set_child(self.listbox)
        main_box.append(self.scrolled)

        self.set_child(main_box)
        self.add_css_class("clipboard-window")

    def load_css(self):
        css_provider = Gtk.CssProvider()
        css = """
        .clipboard-window {
            background: #1a2026;
            border-radius: 16px;
            border: 1px solid #2a3540;
        }

        .search-entry {
            background: #232b33;
            color: #7a8a94;
            border-radius: 10px;
            padding: 14px 16px;
            font-size: 13px;
            min-height: 24px;
            border: 1px solid #2a3540;
        }

        .search-entry:focus {
            border: 1px solid #3a4a55;
        }

        .clipboard-list {
            background: transparent;
        }

        .clipboard-list row {
            background: #252d36;
            border-radius: 10px;
            margin: 8px 0;
            padding: 16px;
            color: #b0c0cc;
            min-height: 40px;
        }

        .clipboard-list row:hover {
            background: #2d3842;
        }

        .clipboard-list row:selected {
            background: #354550;
        }

        .clipboard-text {
            font-size: 13px;
            color: #b0c0cc;
        }

        .clear-button {
            background: #3a2530;
            color: #e07080;
            border-radius: 10px;
            padding: 10px 16px;
            font-size: 12px;
            border: 1px solid #4a3540;
        }

        .clear-button:hover {
            background: #4a3040;
        }

        .empty-label {
            color: #5a6a74;
            font-size: 14px;
            padding: 40px;
        }
        """
        css_provider.load_from_string(css)
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

    def load_clipboard_items(self, search_query=None):
        # Clear existing
        while True:
            row = self.listbox.get_row_at_index(0)
            if row is None:
                break
            self.listbox.remove(row)

        # Get from GPaste
        entries = self.gpaste.get_history(limit=50)

        # Filter by search if needed
        if search_query:
            search_lower = search_query.lower()
            entries = [e for e in entries if search_lower in e['content'].lower()]

        if not entries:
            label = Gtk.Label()
            label.set_text("No clipboard history")
            label.add_css_class("empty-label")
            row = Gtk.ListBoxRow()
            row.set_child(label)
            row.set_activatable(False)
            self.listbox.append(row)
        else:
            for entry in entries:
                content = entry['content']
                label = Gtk.Label()
                display_text = content[:100] + ("..." if len(content) > 100 else "")
                display_text = display_text.replace('\n', ' ')
                label.set_text(display_text)
                label.set_xalign(0)
                label.set_wrap(True)
                label.set_max_width_chars(60)
                label.add_css_class("clipboard-text")

                row = Gtk.ListBoxRow()
                row.set_child(label)
                row.item_index = entry['index']
                self.listbox.append(row)

            # Select first item by default
            first_row = self.listbox.get_row_at_index(0)
            if first_row:
                self.listbox.select_row(first_row)

    def on_search_changed(self, entry):
        query = entry.get_text()
        self.load_clipboard_items(search_query=query if query else None)

    def on_clear_clicked(self, button):
        self.gpaste.clear_history()
        self.load_clipboard_items()

    def paste_and_close(self, row):
        """Copy to clipboard and auto-paste using ydotool"""
        if hasattr(row, 'item_index'):
            self.gpaste.select_item(row.item_index)
            # Run paste command independently with delay, then close
            subprocess.Popen(
                ['bash', '-c', 'sleep 0.1 && ydotool key 29:1 47:1 47:0 29:0'],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                env={**os.environ, 'YDOTOOL_SOCKET': '/tmp/.ydotool_socket'}
            )
            self.close()

    def on_row_activated(self, listbox, row):
        self.paste_and_close(row)

    def on_key_pressed(self, controller, keyval, keycode, state):
        if keyval == Gdk.KEY_Escape:
            self.close()
            return True

        elif keyval == Gdk.KEY_Return or keyval == Gdk.KEY_KP_Enter:
            selected = self.listbox.get_selected_row()
            if selected:
                self.paste_and_close(selected)
            return True

        elif keyval == Gdk.KEY_Down:
            selected = self.listbox.get_selected_row()
            if selected:
                next_row = self.listbox.get_row_at_index(selected.get_index() + 1)
                if next_row:
                    self.listbox.select_row(next_row)
                    next_row.grab_focus()
            return True

        elif keyval == Gdk.KEY_Up:
            selected = self.listbox.get_selected_row()
            if selected and selected.get_index() > 0:
                prev_row = self.listbox.get_row_at_index(selected.get_index() - 1)
                if prev_row:
                    self.listbox.select_row(prev_row)
                    prev_row.grab_focus()
            return True

        return False

    def show_overlay(self):
        self.load_clipboard_items()
        self.present()
        self.search_entry.grab_focus()


class ClipboardManager(Gtk.Application):
    def __init__(self):
        super().__init__(application_id='com.clipboard.manager',
                        flags=Gio.ApplicationFlags.FLAGS_NONE)
        self.overlay = None

    def do_activate(self):
        if not self.overlay:
            self.overlay = ClipboardOverlay(self)
        self.overlay.show_overlay()


def main():
    app = ClipboardManager()
    app.run(sys.argv)


if __name__ == '__main__':
    main()
