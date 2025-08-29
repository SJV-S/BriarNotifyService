#!/bin/bash

# Briar Notify - Command line client
# Makes HTTP requests to the running Briar Notify service

API_BASE="http://localhost:8010"

# Detect if we're running from symlink (installed) or directly (development)
if [[ -L "$0" ]]; then
    # We're a symlink, use production install directory
    INSTALL_DIR="/opt/briar-notify"
else
    # We're running directly, use script's directory for development
    INSTALL_DIR="$(dirname "$0")"
fi

show_usage() {
    echo "Usage: briar-notify <command> [options] [args...]"
    echo ""
    echo "Commands:"
    echo "  send <title> <message>     Send notification to all contacts"
    echo "  status                     Check service status"
    echo "  contacts                   List contacts"
    echo "  create [name]              Create new Briar identity"
    echo "  delete                     Delete current Briar identity"
    echo "  start                      Start briar-notify service"
    echo "  stop                       Stop briar-notify service"
    echo "  service-status             Show service status"
    echo ""
    echo "  help                       Show this help message"
    echo ""
    echo "Options for send command:"
    echo "  --confirm, -c              Wait for confirmation (default: async)"
    echo "  --help, -h                 Show help for specific command"
    echo ""
    echo "Examples:"
    echo "  briar-notify send 'Alert' 'Server is down'           # Send async (no wait)"
    echo "  briar-notify send -c 'Alert' 'Server is down'        # Send with confirmation"
    echo "  briar-notify create alice                            # Create identity"
    echo "  briar-notify start                                   # Start service"
    echo "  briar-notify status"
    echo "  briar-notify contacts"
}

check_service() {
    curl -s "$API_BASE/health" >/dev/null 2>&1
    return $?
}

cmd_send() {
    local confirm=false
    local args=()
    
    # Parse options
    while [[ $# -gt 0 ]]; do
        case $1 in
            --confirm|-c)
                confirm=true
                shift
                ;;
            --help|-h)
                echo "Usage: briar-notify send [options] <title> <message>"
                echo ""
                echo "Options:"
                echo "  --confirm, -c    Wait for confirmation (default: async)"
                echo "  --help, -h       Show this help"
                echo ""
                echo "Examples:"
                echo "  briar-notify send 'Alert' 'Server down'        # Async (no wait)"
                echo "  briar-notify send -c 'Alert' 'Server down'     # With confirmation"
                exit 0
                ;;
            -*)
                echo "Error: Unknown option '$1'"
                echo "Use 'briar-notify send --help' for usage information"
                exit 1
                ;;
            *)
                args+=("$1")
                shift
                ;;
        esac
    done
    
    if [[ ${#args[@]} -lt 2 ]]; then
        echo "Error: send requires title and message"
        echo "Usage: briar-notify send [options] <title> <message>"
        echo "Use 'briar-notify send --help' for more information"
        exit 1
    fi
    
    title="${args[0]}"
    message="${args[1]}"
    
    if [[ "$confirm" == true ]]; then
        # Send with confirmation
        response=$(curl -s -w "%{http_code}" \
            -X POST "$API_BASE/api/send" \
            -H "Content-Type: application/json" \
            -d "{\"title\":\"$title\",\"content\":\"$message\"}")
        
        http_code="${response: -3}"
        body="${response%???}"
        
        if [[ "$http_code" == "200" ]]; then
            echo "✓ Message sent successfully"
        else
            echo "✗ Failed to send message (HTTP $http_code)"
            echo "$body"
            exit 1
        fi
    else
        # Send async (fire and forget)
        curl -s -X POST "$API_BASE/api/send" \
            -H "Content-Type: application/json" \
            -d "{\"title\":\"$title\",\"content\":\"$message\"}" \
            >/dev/null 2>&1 &
        # Exit immediately without waiting
        exit 0
    fi
}

cmd_status() {
    if check_service; then
        echo "✓ Briar Notify service is running"
        
        # Try to get contact status
        response=$(curl -s "$API_BASE/contact-status" 2>/dev/null)
        if [[ $? -eq 0 && -n "$response" ]]; then
            # Parse JSON to get contact_display
            contact_display=$(echo "$response" | grep -o '"contact_display":"[^"]*"' | cut -d'"' -f4)
            if [[ -n "$contact_display" ]]; then
                echo "$contact_display"
            fi
        fi
    else
        echo "✗ Briar Notify service is not running"
        exit 1
    fi
}

cmd_contacts() {
    response=$(curl -s "$API_BASE/get-contacts" 2>/dev/null)
    if [[ $? -eq 0 && -n "$response" ]]; then
        echo "$response"
    else
        echo "✗ Failed to get contacts"
        exit 1
    fi
}

# Check if curl is available
if ! command -v curl >/dev/null 2>&1; then
    echo "Error: curl is required"
    exit 1
fi

# Parse command
if [[ $# -eq 0 ]]; then
    show_usage
    exit 1
fi

command="$1"
shift

case "$command" in
    send)
        if ! check_service; then
            echo "✗ Briar Notify service is not running on $API_BASE"
            exit 1
        fi
        cmd_send "$@"
        ;;
    status)
        cmd_status
        ;;
    contacts)
        if ! check_service; then
            echo "✗ Briar Notify service is not running on $API_BASE"
            exit 1
        fi
        cmd_contacts
        ;;
    create)
        exec "$INSTALL_DIR/briar_notify/venv/bin/python" "$INSTALL_DIR/briar_notify/external_client/identity_manager.py" create "$@"
        ;;
    delete)
        exec "$INSTALL_DIR/briar_notify/venv/bin/python" "$INSTALL_DIR/briar_notify/external_client/identity_manager.py" delete "$@"
        ;;
    start)
        exec bash "$INSTALL_DIR/launch.sh"
        ;;
    stop)
        echo "Stopping Briar Notify Service..."
        pkill -f "briar-headless"
        pkill -f "gunicorn.*web_ui.app"
        echo "Service stopped"
        ;;
    service-status)
        echo "Checking running processes..."
        ps aux | grep -E "(briar-headless|gunicorn.*web_ui.app)" | grep -v grep
        ;;
    help|--help|-h)
        show_usage
        exit 0
        ;;
    *)
        echo "Error: Unknown command '$command'"
        echo ""
        show_usage
        exit 1
        ;;
esac
