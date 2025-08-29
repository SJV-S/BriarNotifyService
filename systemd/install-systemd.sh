#!/bin/bash

# Systemd Installation Script for Briar Notify Service
# Automates the installation and setup of the systemd service

set -e

SCRIPT_DIR="$(dirname "$0")"
INSTALL_ROOT="$(dirname "$SCRIPT_DIR")"
SERVICE_NAME="briar-notify"
SYSTEMD_DIR="$SCRIPT_DIR"

# Check for verbose flag
VERBOSE=false
if [[ "$1" == "-v" ]]; then
    VERBOSE=true
fi

echo "=== Briar Notify Service - Systemd Installation ==="
echo ""

# Check if running as root
if [[ $EUID -eq 0 ]]; then
    echo "ERROR: Do not run this script as root!"
    echo "The script will use sudo when needed."
    exit 1
fi

# Check if systemd directory exists
if [[ ! -d "$SYSTEMD_DIR" ]]; then
    echo "ERROR: systemd directory not found at: $SYSTEMD_DIR"
    echo "Please run this script from the correct installation directory."
    exit 1
fi

# Check if service files exist
if [[ ! -f "$SYSTEMD_DIR/${SERVICE_NAME}.service" ]]; then
    echo "ERROR: Service file not found: $SYSTEMD_DIR/${SERVICE_NAME}.service"
    exit 1
fi

if [[ ! -f "$SYSTEMD_DIR/systemd-launch.sh" ]]; then
    echo "ERROR: Launch script not found: $SYSTEMD_DIR/systemd-launch.sh"
    exit 1
fi

# Check prerequisites
echo "Checking prerequisites..."

# Check if identity exists
if ! "$INSTALL_ROOT/briar_notify/venv/bin/python" -c "
import sys
from pathlib import Path
sys.path.insert(0, '$INSTALL_ROOT/briar_notify')
from internal_service.briar_service import get_identity_name
if not get_identity_name():
    exit(1)
" 2>/dev/null; then
    echo "ERROR: No Briar identity found!"
    echo "Please create an identity first:"
    echo "  ./briar-notify.sh create <nickname>"
    exit 1
fi

# Check if password file exists
if [[ ! -f "$HOME/.briar-notify/briar-password" ]]; then
    echo "ERROR: Password file not found: $HOME/.briar-notify/briar-password"
    echo "Please ensure your Briar identity is properly set up."
    exit 1
fi

echo "✓ Prerequisites check passed"
echo ""

# Stop existing service if running
if systemctl is-active --quiet "${SERVICE_NAME}" 2>/dev/null; then
    echo "Stopping existing ${SERVICE_NAME} service..."
    sudo systemctl stop "${SERVICE_NAME}"
fi

# Stop manual processes if running  
if pgrep -f "briar-headless" >/dev/null || pgrep -f "gunicorn.*web_ui.app" >/dev/null; then
    echo "Stopping existing manual processes..."
    pkill -f "briar-headless" 2>/dev/null || true
    pkill -f "gunicorn.*web_ui.app" 2>/dev/null || true
    sleep 2
fi

# Install service file with current user
echo "Installing systemd service file..."
sed "s/User=owl/User=$USER/g; s/Group=owl/Group=$USER/g" "$SYSTEMD_DIR/${SERVICE_NAME}.service" > /tmp/${SERVICE_NAME}.service
# Ensure the file ends with a newline (systemd requirement)
echo "" >> /tmp/${SERVICE_NAME}.service
sudo mv /tmp/${SERVICE_NAME}.service /etc/systemd/system/
# Fix SELinux context if SELinux is enabled
if command -v restorecon >/dev/null 2>&1; then
    sudo restorecon /etc/systemd/system/${SERVICE_NAME}.service
fi

# Reload systemd configuration  
echo "Reloading systemd configuration..."
sudo systemctl daemon-reload

# Enable service (auto-start at boot)
echo "Enabling ${SERVICE_NAME} service..."
sudo systemctl enable "${SERVICE_NAME}"

# Start the service
echo "Starting ${SERVICE_NAME} service..."
sudo systemctl start "${SERVICE_NAME}"

# Wait a moment for startup
sleep 3

# Check service status
if [[ "$VERBOSE" == true ]]; then
    echo ""
    echo "=== Service Status ==="
    sudo systemctl status "${SERVICE_NAME}" --no-pager -l
fi



