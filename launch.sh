#!/bin/bash

# Detect install directory
script_dir="$(dirname "$0")"
if [[ -d "$script_dir/briar_notify/internal_service" ]]; then
    INSTALL_DIR="$script_dir"
else
    INSTALL_DIR="/opt/briar-notify"
fi

# Check for already running processes and stop them
if pgrep -f "briar-headless" >/dev/null || pgrep -f "gunicorn.*web_ui.app" >/dev/null; then
    echo "Existing Briar Notify processes found - restarting..."
    echo "   Stopping Briar JAR..."
    pkill -f "briar-headless" 2>/dev/null
    echo "   Stopping Flask web interface..."
    pkill -f "gunicorn.*web_ui.app" 2>/dev/null
    echo "   Waiting for processes to stop..."
    sleep 2
    echo "Previous processes stopped"
    echo ""
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
    print("  briar-notify identity create <nickname>")
    print("")
    print("Example:")
    print("  briar-notify identity create alice")
    exit(1)
else:
    print(f"Using identity: {identity_name}")
IDENTITY_CHECK

# Start Briar JAR and WAIT for it to be ready
echo "Starting Briar headless JAR..."
INSTALL_DIR="$INSTALL_DIR" "$INSTALL_DIR/briar_notify/venv/bin/python" - <<'EOF'
import sys
from pathlib import Path
import os
INSTALL_DIR = Path(os.environ.get('INSTALL_DIR', '/opt/briar-notify'))
sys.path.insert(0, str(INSTALL_DIR / 'briar_notify'))

BRIAR_CONFIG_DIR = Path.home() / '.briar-notify'
BRIAR_PASSWORD_FILE = BRIAR_CONFIG_DIR / 'briar-password'
password = BRIAR_PASSWORD_FILE.read_text().strip()

from internal_service.briar_service import start_briar_process, wait_for_briar_ready
from internal_service.password_manager import password_manager

# Load password into memory for the service
password_manager.set_identity_password(password)

start_briar_process(password + '\n')
wait_for_briar_ready()
print('Briar JAR is ready')
EOF

export FLASK_ENV=production

LOCAL_IP=$(hostname -I | awk '{print $1}')

echo "Starting Briar Notify Service (Production)..."
echo ""
echo "Web interface will be available at:"
echo "   Local:   http://localhost:8010"
echo "   Network: http://$LOCAL_IP:8010"
echo ""

# Start Flask in background
cd "$INSTALL_DIR/briar_notify"
nohup "$INSTALL_DIR/briar_notify/venv/bin/gunicorn" \
    --bind 0.0.0.0:8010 \
    --workers 1 \
    --worker-class gevent \
    web_ui.app:app &

disown

# Exit so terminal returns to prompt
exit 0
