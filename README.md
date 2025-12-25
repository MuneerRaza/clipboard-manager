# Clipboard Manager for GNOME

A lightweight, Windows-like clipboard manager for GNOME on Wayland.

![Platform](https://img.shields.io/badge/Platform-GNOME%20Wayland-blue)
![License](https://img.shields.io/badge/License-MIT-yellow)

## Features

- **Windows-like UI** - Press `Super+V` to open clipboard history
- **Auto-paste** - Select an item and it pastes directly where your cursor is
- **Search** - Quickly filter clipboard history
- **Keyboard navigation** - Arrow keys + Enter to select
- **Click outside to close** - Just like Windows
- **Lightweight** - less memory usage
- **Event-driven** - No polling, uses GPaste daemon

## Screenshots
<img width="540" height="540" alt="image" src="https://github.com/user-attachments/assets/10b74680-788f-4a86-a4fd-3e2f3356736c" />



## Requirements

- GNOME Desktop (tested on GNOME 47+)
- Wayland session
- Fedora / Ubuntu / Arch Linux

## Installation

### Quick Install (Fedora)

```bash
git clone https://github.com/yourusername/clipboard-manager.git
cd clipboard-manager
chmod +x install.sh
./install.sh
```

### Manual Installation

1. **Install dependencies:**

```bash
# Fedora
sudo dnf install gpaste ydotool python3-gobject gtk4

# Ubuntu/Debian
sudo apt install gpaste ydotool python3-gi gir1.2-gtk-4.0

# Arch
sudo pacman -S gpaste ydotool python-gobject gtk4
```

2. **Setup ydotool daemon:**

```bash
# Create systemd service
sudo tee /etc/systemd/system/ydotool.service << 'EOF'
[Unit]
Description=ydotool daemon
After=multi-user.target

[Service]
ExecStart=/usr/bin/ydotoold --socket-path /tmp/.ydotool_socket --socket-perm 0666
Restart=on-failure

[Install]
WantedBy=multi-user.target
EOF

# Enable and start
sudo systemctl daemon-reload
sudo systemctl enable ydotool
sudo systemctl start ydotool
```

3. **Install clipboard manager:**

```bash
# Copy main script
sudo cp src/clipboard_manager.py /usr/local/bin/clipboard-manager
sudo chmod +x /usr/local/bin/clipboard-manager

# Create desktop entry
mkdir -p ~/.local/share/applications
cat > ~/.local/share/applications/clipboard-manager.desktop << 'EOF'
[Desktop Entry]
Name=Clipboard Manager
Comment=Windows-like clipboard manager for GNOME
Exec=/usr/local/bin/clipboard-manager
Icon=edit-paste
Terminal=false
Type=Application
Categories=Utility;
NoDisplay=true
EOF
```

4. **Set keyboard shortcut:**

   - Open **Settings** → **Keyboard** → **Custom Shortcuts**
   - Add new shortcut:
     - Name: `Clipboard Manager`
     - Command: `/usr/local/bin/clipboard-manager`
     - Shortcut: `Super+V`

## Usage

| Key | Action |
|-----|--------|
| `Super+V` | Open clipboard manager |
| `↑` / `↓` | Navigate items |
| `Enter` | Paste selected item |
| `Escape` | Close without pasting |
| Click outside | Close without pasting |

## How It Works

```
┌─────────────────────────────────────────────┐
│              GNOME / Mutter                  │
│            (Clipboard system)                │
└──────────────────┬──────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────┐
│           GPaste Daemon (~34MB)              │
│   - Hooks into clipboard at system level    │
│   - Event-driven (no polling)               │
│   - Stores history automatically            │
└──────────────────┬──────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────┐
│         Clipboard Manager UI (Python)        │
│   - Queries GPaste via CLI                  │
│   - Beautiful dark overlay                  │
│   - Auto-paste via ydotool                  │
└──────────────────┬──────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────┐
│           ydotool Daemon (~2MB)              │
│   - Simulates Ctrl+V keystroke              │
│   - Works on Wayland (uses uinput)          │
└─────────────────────────────────────────────┘
```

## Uninstallation

```bash
./uninstall.sh
```

Or manually:

```bash
sudo rm /usr/local/bin/clipboard-manager
rm ~/.local/share/applications/clipboard-manager.desktop
sudo systemctl disable ydotool
sudo systemctl stop ydotool
sudo rm /etc/systemd/system/ydotool.service
sudo dnf remove gpaste ydotool  # or apt/pacman
```

## Troubleshooting

### Auto-paste not working

Make sure ydotool daemon is running:
```bash
sudo systemctl status ydotool
```

### Clipboard history not updating

Restart GPaste daemon:
```bash
gpaste-client daemon-reexec
```

### Super+V not working

Check if the keyboard shortcut is set correctly in GNOME Settings.

## License

MIT License - feel free to use and modify!

## Contributing

Pull requests welcome! Please open an issue first to discuss changes.

## Credits

- [GPaste](https://github.com/Keruspe/GPaste) - Clipboard management daemon
- [ydotool](https://github.com/ReimuNotMoe/ydotool) - Wayland-compatible input simulation
