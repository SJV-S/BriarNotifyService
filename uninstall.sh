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

echo "Removing installation directory..."
echo "   Removing /opt/briar-notify..."
sudo rm -rf "/opt/briar-notify"
echo "Removed /opt/briar-notify"
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
echo "  - Application files from /opt/briar-notify"
echo "  - Systemd service integration"
echo "  - Command symlink from /usr/local/bin/briar-notify"
if [[ "$USER_DATA_REMOVED" == "true" ]]; then
    echo "  - User data from ~/.briar-notify/ and ~/.briar/"
fi
echo ""

