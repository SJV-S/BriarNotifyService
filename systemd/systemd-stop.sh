#!/bin/bash

# Systemd stop wrapper for Briar Notify Service
# Gracefully shuts down both Briar JAR and Flask GUI

echo "Stopping Briar Notify Service..."

BRIAR_PID_FILE="/tmp/briar-notify-jar.pid"

# Stop Briar JAR first (gracefully)
if [[ -f "$BRIAR_PID_FILE" ]]; then
    BRIAR_PID=$(cat "$BRIAR_PID_FILE")
    if kill -0 "$BRIAR_PID" 2>/dev/null; then
        echo "Stopping Briar JAR (PID: $BRIAR_PID)..."
        kill -TERM "$BRIAR_PID" 2>/dev/null || true
        
        # Wait up to 15 seconds for graceful shutdown
        for i in {1..15}; do
            if ! kill -0 "$BRIAR_PID" 2>/dev/null; then
                echo "Briar JAR stopped gracefully"
                break
            fi
            sleep 1
        done
        
        # Force kill if still running
        if kill -0 "$BRIAR_PID" 2>/dev/null; then
            echo "Force killing Briar JAR..."
            kill -9 "$BRIAR_PID" 2>/dev/null || true
        fi
    fi
    rm -f "$BRIAR_PID_FILE"
fi

# Stop Flask/Gunicorn (systemd will handle this, but ensure cleanup)
echo "Stopping Flask web interface..."
pkill -TERM -f "gunicorn.*web_ui.app" 2>/dev/null || true

# Wait a moment for graceful shutdown
sleep 2

# Force kill any remaining processes
echo "Cleaning up remaining processes..."
pkill -9 -f "briar-headless" 2>/dev/null || true
pkill -9 -f "gunicorn.*web_ui.app" 2>/dev/null || true

# Clean up any Tor processes started by Briar
pkill -9 -f "tor.*briar" 2>/dev/null || true

echo "Briar Notify Service stopped"