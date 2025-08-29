#!/bin/bash

echo "=== Briar Notify Service - Uninstaller ==="
echo ""
echo "Uninstall Overview"
echo "=============================================="
echo "  - Stop running services and processes"
echo "  - Remove systemd service integration"
echo "  - Remove installation directory"
echo "  - Remove command symlink"
echo "  - Optionally remove user data"
echo ""

echo "Stopping services..."
# Stop systemd service if exists
if systemctl is-active --quiet briar-notify 2>/dev/null; then
    echo "   Stopping systemd service..."
    sudo systemctl stop briar-notify
    echo "   Service stopped"
fi

if systemctl is-enabled --quiet briar-notify 2>/dev/null; then
    echo "   Disabling systemd service..."
    sudo systemctl disable briar-notify
    echo "   Service disabled"
fi

if [ -f "/etc/systemd/system/briar-notify.service" ]; then
    echo "   Removing systemd service file..."
    sudo rm /etc/systemd/system/briar-notify.service
    sudo systemctl daemon-reload
    echo "   Service file removed"
fi
echo ""

echo "Stopping processes..."
if pgrep -f "briar-headless" >/dev/null; then
    echo "   Stopping Briar JAR..."
    pkill -f "briar-headless" 2>/dev/null
fi

if pgrep -f "gunicorn.*briar_notify.web_ui" >/dev/null; then
    echo "   Stopping Flask web interface..."
    pkill -f "gunicorn.*briar_notify.web_ui" 2>/dev/null
fi

echo "   Waiting for processes to stop..."
sleep 3
echo "Processes stopped"
echo ""

echo "Removing command symlink..."
if [ -L "/usr/local/bin/briar-notify" ]; then
    sudo rm /usr/local/bin/briar-notify
    echo "Removed /usr/local/bin/briar-notify"
else
    echo "   Symlink not found (already removed)"
fi
echo ""

# Detect install directory
script_dir="$(dirname "$0")"
if [[ -d "$script_dir/briar_notify/internal_service" ]]; then
    INSTALL_DIR="$script_dir"
    IS_OPT_INSTALL=false
else
    INSTALL_DIR="/opt/briar-notify"
    IS_OPT_INSTALL=true
fi

echo "Removing installation directory..."
if [ -d "$INSTALL_DIR" ] && [ "$IS_OPT_INSTALL" = true ]; then
    echo "   Removing $INSTALL_DIR..."
    sudo rm -rf "$INSTALL_DIR"
    echo "Removed $INSTALL_DIR"
elif [ "$IS_OPT_INSTALL" = false ]; then
    echo "   Local installation detected - cleaning up files..."
    rm -rf "$INSTALL_DIR/briar_notify/venv" 2>/dev/null
    echo "Removed virtual environment"
else
    echo "   Installation directory not found"
fi
echo ""

echo "User Data Removal"
echo "=============================================="
echo "Do you want to remove user data? This includes:"
echo "   - Briar identity and private keys"
echo "   - All contacts and conversations"
echo "   - All scheduled messages"
echo "   - Configuration files"
echo ""
echo "Location: ~/.briar-notify/"
echo ""
read -p "Remove user data? [y/N]: " -r

if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo ""
    echo "Removing user data..."
    if [ -d "$HOME/.briar-notify" ]; then
        rm -rf "$HOME/.briar-notify"
        rm -rf "$HOME/.briar"
        echo "Removed $HOME/.briar-notify"
        echo "Removed $HOME/.briar"
        USER_DATA_REMOVED=true
    else
        echo "   User data directory not found"
        USER_DATA_REMOVED=false
    fi
else
    echo ""
    echo "User data preserved in $HOME/.briar-notify"
    echo "User data preserved in $HOME/.briar"
    USER_DATA_REMOVED=false
fi

echo "=== Uninstall Complete ==="
echo "=============================================="
echo ""
echo "Briar Notify Service has been completely removed from your system."
echo ""
echo "What was removed:"
echo "  - Application files from $INSTALL_DIR"
echo "  - Systemd service integration"
echo "  - Command symlink from /usr/local/bin/briar-notify"
if [[ "$USER_DATA_REMOVED" == "true" ]]; then
    echo "  - User data from ~/.briar-notify/ and ~/.briar/"
fi
echo ""

