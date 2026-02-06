#!/usr/bin/python3
"""
Clipboard Manager UI for GNOME Wayland
Uses GPaste daemon as backend (event-driven, no polling)
Uses ydotool for auto-paste
Supports text and images
"""

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Gdk', '4.0')
gi.require_version('GdkPixbuf', '2.0')
from gi.repository import Gtk, Gdk, Gio, GLib, GdkPixbuf
import subprocess
import sys
import os
import re
import html

# Set ydotool socket path
os.environ['YDOTOOL_SOCKET'] = '/tmp/.ydotool_socket'


class GPasteClient:
    """Interface to GPaste daemon via CLI"""

    def __init__(self):
        self.gpaste_images_dir = os.path.expanduser('~/.local/share/gpaste/images')
        self.history_file = os.path.expanduser('~/.local/share/gpaste/history.xml')

    def _parse_image_paths(self):
        """Read history.xml once and extract all image paths into a dict"""
        paths = {}
        try:
            with open(self.history_file, 'r') as f:
                xml_content = f.read()
            for match in re.finditer(
                r'<item kind="Image" uuid="([^"]+)"[^>]*>.*?<value><!\[CDATA\[(.*?)\]\]></value>',
                xml_content, re.DOTALL
            ):
                paths[match.group(1)] = match.group(2)
        except Exception:
            pass
        return paths

    def get_history(self, limit=30):
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
            image_paths = None
            lines = result.stdout.strip().split('\n')
            for i, line in enumerate(lines[:limit]):
                if ':' in line:
                    parts = line.split(':', 1)
                    if len(parts) == 2:
                        uuid = parts[0].strip()
                        content = parts[1].strip()
                        if content:
                            is_image = content.startswith('[Image,')
                            image_path = None
                            if is_image:
                                if image_paths is None:
                                    image_paths = self._parse_image_paths()
                                image_path = image_paths.get(uuid)
                            entries.append({
                                'index': i,
                                'uuid': uuid,
                                'content': html.unescape(content),
                                'is_image': is_image,
                                'image_path': image_path
                            })
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
        window.clipboard-window,
        .clipboard-window {
            background-color: #14161c;
            border-radius: 16px;
            border: 1px solid rgba(255, 255, 255, 0.06);
        }

        window.clipboard-window > * {
            border-radius: 16px;
        }

        .search-entry {
            background: rgba(255, 255, 255, 0.06);
            color: rgba(255, 255, 255, 0.95);
            border-radius: 10px;
            padding: 8px 14px;
            font-size: 14px;
            min-height: 18px;
            border: 1px solid rgba(255, 255, 255, 0.1);
        }

        .search-entry:focus {
            background: rgba(255, 255, 255, 0.08);
            border: 1px solid rgba(100, 160, 255, 0.4);
        }

        .clipboard-list {
            background: transparent;
        }

        scrollbar {
            opacity: 0;
        }

        .clipboard-list row {
            background: rgba(255, 255, 255, 0.04);
            border-radius: 12px;
            margin: 4px 0;
            padding: 12px 16px;
            color: rgba(255, 255, 255, 0.9);
            min-height: 28px;
            border: 1px solid rgba(255, 255, 255, 0.06);
        }

        .clipboard-list row:hover {
            background: rgba(255, 255, 255, 0.08);
            border: 1px solid rgba(255, 255, 255, 0.12);
        }

        .clipboard-list row:selected {
            background: rgba(100, 160, 255, 0.12);
            border: 1px solid rgba(100, 160, 255, 0.3);
        }

        .clipboard-text {
            font-size: 13px;
            font-weight: 400;
            color: rgba(255, 255, 255, 0.88);
            line-height: 1.5;
        }

        .clear-button {
            background: rgba(255, 90, 90, 0.15);
            color: #ff9090;
            border-radius: 10px;
            padding: 8px 16px;
            font-size: 13px;
            font-weight: 500;
            border: 1px solid rgba(255, 100, 100, 0.25);
        }

        .clear-button:hover {
            background: rgba(255, 90, 90, 0.25);
            border: 1px solid rgba(255, 100, 100, 0.4);
        }

        .empty-label {
            color: rgba(255, 255, 255, 0.35);
            font-size: 14px;
            font-weight: 400;
            padding: 60px;
        }

        .image-thumbnail {
            border-radius: 10px;
            border: 1px solid rgba(255, 255, 255, 0.08);
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
        entries = self.gpaste.get_history(limit=30)

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
                row = Gtk.ListBoxRow()
                row.item_index = entry['index']
                row.is_image = entry.get('is_image', False)

                if entry.get('is_image') and entry.get('image_path'):
                    # Image entry - show thumbnail
                    image_path = entry['image_path']
                    if os.path.exists(image_path):
                        try:
                            pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(
                                image_path,
                                width=460,
                                height=200,
                                preserve_aspect_ratio=True
                            )
                            texture = Gdk.Texture.new_for_pixbuf(pixbuf)
                            image = Gtk.Picture.new_for_paintable(texture)
                            image.set_content_fit(Gtk.ContentFit.CONTAIN)
                            image.set_can_shrink(False)
                            image.add_css_class("image-thumbnail")
                            row.set_child(image)
                        except Exception:
                            label = Gtk.Label(label="Image")
                            label.add_css_class("clipboard-text")
                            row.set_child(label)
                    else:
                        label = Gtk.Label(label="Image")
                        label.add_css_class("clipboard-text")
                        row.set_child(label)
                else:
                    # Text entry - show up to 4 lines preview
                    content = entry['content']
                    lines = content.split('\n')
                    display_lines = []
                    for line in lines[:4]:
                        clean_line = ' '.join(line.split())
                        if len(clean_line) > 70:
                            clean_line = clean_line[:70] + "..."
                        if clean_line:
                            display_lines.append(clean_line)
                    display_text = '\n'.join(display_lines) if display_lines else content[:70]
                    if len(lines) > 4:
                        display_text += "\n..."
                    label = Gtk.Label(label=display_text)
                    label.set_xalign(0)
                    label.set_yalign(0)
                    label.set_max_width_chars(70)
                    label.add_css_class("clipboard-text")
                    row.set_child(label)

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
        # Focus first item so Enter pastes immediately
        first_row = self.listbox.get_row_at_index(0)
        if first_row and first_row.get_activatable():
            first_row.grab_focus()


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
