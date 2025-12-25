#!/bin/bash
#
# Clipboard Manager Installer for GNOME Wayland
# Supports: Fedora, Ubuntu/Debian, Arch Linux
#

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  Clipboard Manager Installer${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Detect package manager
detect_distro() {
    if command -v dnf &> /dev/null; then
        PKG_MANAGER="dnf"
        PACKAGES="gpaste ydotool python3-gobject gtk4"
    elif command -v apt &> /dev/null; then
        PKG_MANAGER="apt"
        PACKAGES="gpaste ydotool python3-gi gir1.2-gtk-4.0"
    elif command -v pacman &> /dev/null; then
        PKG_MANAGER="pacman"
        PACKAGES="gpaste ydotool python-gobject gtk4"
    else
        echo -e "${RED}Error: Unsupported distribution. Please install manually.${NC}"
        exit 1
    fi
}

# Install dependencies
install_deps() {
    echo -e "${YELLOW}[1/4] Installing dependencies...${NC}"
    case $PKG_MANAGER in
        dnf)
            sudo dnf install -y $PACKAGES
            ;;
        apt)
            sudo apt update
            sudo apt install -y $PACKAGES
            ;;
        pacman)
            sudo pacman -S --noconfirm $PACKAGES
            ;;
    esac
    echo -e "${GREEN}Dependencies installed!${NC}"
}

# Setup ydotool daemon
setup_ydotool() {
    echo -e "${YELLOW}[2/4] Setting up ydotool daemon...${NC}"

    # Create systemd service
    sudo tee /etc/systemd/system/ydotool.service > /dev/null << 'EOF'
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

    echo -e "${GREEN}ydotool daemon configured!${NC}"
}

# Install clipboard manager
install_app() {
    echo -e "${YELLOW}[3/4] Installing clipboard manager...${NC}"

    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

    # Copy main script
    sudo cp "$SCRIPT_DIR/src/clipboard_manager.py" /usr/local/bin/clipboard-manager
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

    echo -e "${GREEN}Clipboard manager installed!${NC}"
}

# Print keyboard shortcut instructions
print_shortcut_instructions() {
    echo -e "${YELLOW}[4/4] Setting up keyboard shortcut...${NC}"
    echo ""
    echo -e "${GREEN}Almost done! Please set up the keyboard shortcut manually:${NC}"
    echo ""
    echo "  1. Open Settings -> Keyboard -> Keyboard Shortcuts"
    echo "  2. Scroll down and click 'Custom Shortcuts'"
    echo "  3. Click '+' to add new shortcut"
    echo "  4. Set:"
    echo "     - Name: Clipboard Manager"
    echo "     - Command: /usr/local/bin/clipboard-manager"
    echo "     - Shortcut: Super+V"
    echo ""
}

# Main
main() {
    detect_distro
    echo -e "Detected package manager: ${GREEN}$PKG_MANAGER${NC}"
    echo ""

    install_deps
    setup_ydotool
    install_app
    print_shortcut_instructions

    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}  Installation Complete!${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
    echo "You can now press Super+V to open clipboard manager"
    echo "(after setting up the keyboard shortcut)"
    echo ""
}

main "$@"
