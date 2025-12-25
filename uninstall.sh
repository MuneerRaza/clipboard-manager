#!/bin/bash
#
# Clipboard Manager Uninstaller
#

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${RED}========================================${NC}"
echo -e "${RED}  Clipboard Manager Uninstaller${NC}"
echo -e "${RED}========================================${NC}"
echo ""

read -p "Are you sure you want to uninstall? (y/N): " confirm
if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
    echo "Cancelled."
    exit 0
fi

echo ""
echo -e "${YELLOW}[1/4] Removing clipboard manager...${NC}"
sudo rm -f /usr/local/bin/clipboard-manager
rm -f ~/.local/share/applications/clipboard-manager.desktop
echo -e "${GREEN}Done!${NC}"

echo -e "${YELLOW}[2/4] Stopping ydotool daemon...${NC}"
sudo systemctl stop ydotool 2>/dev/null || true
sudo systemctl disable ydotool 2>/dev/null || true
sudo rm -f /etc/systemd/system/ydotool.service
sudo systemctl daemon-reload
echo -e "${GREEN}Done!${NC}"

echo -e "${YELLOW}[3/4] Removing socket file...${NC}"
sudo rm -f /tmp/.ydotool_socket
echo -e "${GREEN}Done!${NC}"

echo ""
echo -e "${YELLOW}[4/4] Optional: Remove dependencies${NC}"
echo ""
echo "The following packages were installed:"
echo "  - gpaste"
echo "  - ydotool"
echo ""
echo "To remove them, run:"
echo ""

# Detect package manager
if command -v dnf &> /dev/null; then
    echo "  sudo dnf remove gpaste ydotool"
elif command -v apt &> /dev/null; then
    echo "  sudo apt remove gpaste ydotool"
elif command -v pacman &> /dev/null; then
    echo "  sudo pacman -R gpaste ydotool"
fi

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  Uninstallation Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Don't forget to remove the Super+V keyboard shortcut from Settings."
echo ""
