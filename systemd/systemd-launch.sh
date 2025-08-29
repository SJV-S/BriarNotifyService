#!/bin/bash

# Systemd launch wrapper for Briar Notify Service
# This script starts and monitors both Briar JAR and Flask GUI
# If either process dies, the script exits so systemd can restart everything

set -e

INSTALL_DIR="${INSTALL_DIR:-/opt/briar-notify}"
FLASK_PID_FILE="/tmp/briar-notify-flask.pid"
MONITOR_INTERVAL=5

# Read password once at startup for reuse
BRIAR_CONFIG_DIR="$HOME/.briar-notify"
BRIAR_PASSWORD_FILE="$BRIAR_CONFIG_DIR/briar-password"

# No JAR handling - Flask will manage it

# Function to start Flask
start_flask() {
    echo "Starting Flask GUI..."
    cd "$INSTALL_DIR/briar_notify"
    "$INSTALL_DIR/briar_notify/venv/bin/gunicorn" \
        --bind 0.0.0.0:8010 \
        --workers 1 \
        --worker-class gevent \
        web_ui.app:app &
    
    local flask_pid=$!
    echo "$flask_pid" > "$FLASK_PID_FILE"
    echo "Flask started with PID: $flask_pid"
}

# Function to check if Flask is running
is_flask_running() {
    if [[ -f "$FLASK_PID_FILE" ]]; then
        local pid=$(cat "$FLASK_PID_FILE")
        if kill -0 "$pid" 2>/dev/null; then
            return 0  # Process is running
        fi
    fi
    return 1  # Process is not running
}

# Cleanup function for graceful exit
cleanup() {
    echo "Shutting down Flask service..."
    
    # Kill Flask
    if [[ -f "$FLASK_PID_FILE" ]]; then
        FLASK_PID=$(cat "$FLASK_PID_FILE")
        if kill -0 "$FLASK_PID" 2>/dev/null; then
            echo "Stopping Flask (PID: $FLASK_PID)..."
            kill "$FLASK_PID" 2>/dev/null || true
        fi
        rm -f "$FLASK_PID_FILE"
    fi
    
    # Kill any remaining Flask processes
    pkill -f "gunicorn.*web_ui.app" 2>/dev/null || true
    
    exit 0
}

# Set up signal handlers
trap cleanup SIGTERM SIGINT EXIT

echo "Starting Flask service for systemd..."

# Check for already running Flask processes and stop them
if pgrep -f "gunicorn.*web_ui.app" >/dev/null; then
    echo "Existing Flask processes found - stopping them..."
    pkill -f "gunicorn.*web_ui.app" 2>/dev/null || true
    sleep 2
fi

# Check if identity exists before starting service
"$INSTALL_DIR/briar_notify/venv/bin/python" - <<'IDENTITY_CHECK'
import sys
from pathlib import Path
import os
INSTALL_DIR = Path(os.environ.get('INSTALL_DIR', '/opt/briar-notify'))
sys.path.insert(0, str(INSTALL_DIR / 'briar_notify'))

from internal_service.briar_service import get_identity_name

identity_name = get_identity_name()
if not identity_name:
    print("ERROR: No Briar identity found")
    print("")
    print("Please create an identity first:")
    print("  briar-notify create <nickname>")
    exit(1)
else:
    print(f"Using identity: {identity_name}")
IDENTITY_CHECK

# Check if password file exists - if not, exit gracefully without restart spam
if [[ ! -f "$BRIAR_PASSWORD_FILE" ]]; then
    echo "WARNING: Password file not found: $BRIAR_PASSWORD_FILE"
    echo "This usually means:"
    echo "  - No Briar identity has been created yet"
    echo "  - Identity is being recreated/deleted"
    echo "  - Password file was accidentally removed"
    echo ""
    echo "To fix this:"
    echo "  - Create identity: briar-notify create <nickname>"
    echo "  - Or wait if identity recreation is in progress"
    echo ""
    echo "Service will not start until password file exists."
    echo "systemd will not attempt restart (use 'exit 0' to prevent restart loop)"
    exit 0
fi

export FLASK_ENV=production
LOCAL_IP=$(hostname -I | awk '{print $1}')

echo "Web interface will be available at:"
echo "   Local:   http://localhost:8010"
echo "   Network: http://$LOCAL_IP:8010"
echo ""

# Start Flask only
start_flask

echo "Flask service started. Monitoring..."

# Monitor Flask process - if it dies, exit so systemd restarts
while true; do
    sleep $MONITOR_INTERVAL
    
    if ! is_flask_running; then
        echo "ERROR: Flask process died! Exiting for systemd restart..."
        exit 1
    fi
    
    # Optional: Print status every few cycles
    echo "Flask process still running..."
done