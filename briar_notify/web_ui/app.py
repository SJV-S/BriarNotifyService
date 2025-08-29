
import time
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, jsonify
from internal_service.briar_service import get_identity_invite_link, start_briar_process, wait_for_briar_ready, logout_identity, delete_identity, add_contact, get_contacts, remove_contact, broadcast_message, get_contact_info, identity_running, get_identity_name
from internal_service.scheduler import get_scheduler
from internal_service.password_manager import password_manager
from internal_service.service_config import DEFAULT_WEB_UI_PORT, DEFAULT_BRIAR_PORT, JAVA_PATH, BRIAR_JAR_PATH, BRIAR_NOTIFY_DIR
from internal_service.event_listener import start_event_listener
from internal_service.dead_mans_switch import get_dead_mans_switch
from internal_service.jar_monitor import jar_monitor

app = Flask(__name__)

# Load password into memory at startup
password_manager.load_password_into_memory()

# Start JAR monitoring
jar_monitor.start_monitoring()

def _initialize_processes(password: str):
    scheduler = get_scheduler()
    app.message_scheduler = scheduler
    password_manager.set_identity_password(password)
    start_event_listener()


def _cleanup_scheduler():
    """Stop and cleanup the message scheduler."""
    scheduler = getattr(app, 'message_scheduler', None)

    if scheduler:
        password_manager.clear_identity_password()
        delattr(app, 'message_scheduler')


def _check_identity_running():
    """Check if Briar identity is running and return appropriate error response if not.
    
    Returns:
        tuple: (is_running: bool, error_response: dict or None)
    """
    if not identity_running():
        if not get_identity_name():
            return False, jsonify({'success': False, 'error': 'No identity found', 'redirect': '/'})
        else:
            return False, jsonify({'success': False, 'error': 'Briar identity not running', 'redirect': '/start-identity'})
    return True, None

# Disable caching
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

@app.route('/')
def dashboard():
    
    # Fast check - if identity doesn't exist, redirect immediately
    identity_name = get_identity_name()
    from pathlib import Path
    import os
    
    # Try direct filesystem calls
    import os.path
    
    if BRIAR_NOTIFY_DIR.exists():
        hash_files = list(BRIAR_NOTIFY_DIR.glob('*.hash'))
        # Try with os.listdir too
        try:
            os_files = os.listdir(str(BRIAR_NOTIFY_DIR))
        except Exception as e:
    if not identity_name:
        return redirect('/identity-setup-required')
    
    
    # Load system password into memory if not already loaded
    if password_manager.identity_password is None:
        if not password_manager.load_password_into_memory():
            # Cannot load password - redirect to create new identity
            return redirect('/identity-setup-required')
    
    # Check if identity is running (includes password check)
    if not identity_running():
        # Try to start Briar with system password
        system_password = password_manager.identity_password
        if system_password:
            # Kill any existing process first (don't waste time checking if running)
            logout_identity()
            time.sleep(1)  # Reduced from 3 seconds
            
            # Start Briar with system password
            proc = start_briar_process(system_password, DEFAULT_BRIAR_PORT)
            
            # Wait for Briar API to be ready
            if wait_for_briar_ready():
                _initialize_processes(system_password)
            else:
                # Could not start Briar - redirect to create new identity
                return redirect('/identity-setup-required')
        else:
            # No system password available
            return redirect('/identity-setup-required')

    # Get contact information
    contact_info = get_contact_info()
    if contact_info:
        contact_display = f"Contacts: {contact_info['online_contacts']}/{contact_info['total_contacts']} online"
    else:
        contact_display = "Contacts: 0/0 online"

    invite_link = get_identity_invite_link()
    return render_template('dashboard.html', 
                         status="Container Running",
                         briar_status="Connected",
                         contact_display=contact_display,
                         identity=invite_link,
                         identity_name=identity_name)

@app.route('/identity-setup-required')
def identity_setup_required():
    return '''
    <html>
    <head><title>Create Identity Required</title></head>
    <body style="font-family: Arial, sans-serif; margin: 60px auto; max-width: 600px; background: white;">
        <h2>No Identity Found</h2>
        <p>Create a Briar identity using the command line:</p>
        <pre style="background: #f0f0f0; padding: 12px; font-family: monospace;">briar-notify identity create &lt;nickname&gt;</pre>
        <p>Then refresh this page.</p>
        <a href="/">← Back to Dashboard</a>
    </body>
    </html>
    '''


@app.route('/create-identity', methods=['POST'])
def create_identity():
    nickname = request.form['nickname']
    
    # Create auto-generated password
    auto_password = password_manager.create_auto_generated_identity_password(nickname)
    if not auto_password:
        # Failed to generate/save password
        return redirect('/identity-setup-required')
    
    # Kill any existing Briar processes
    logout_identity()
    time.sleep(2)
    
    # Start Briar with identity creation data using auto-generated password
    input_data = f"{nickname}\n{auto_password}\n{auto_password}\n"
    proc = start_briar_process(input_data, DEFAULT_BRIAR_PORT)
    
    # Wait for Briar API to be ready
    if wait_for_briar_ready():
        # Save password verification hash
        password_manager.save_password_verification_hash(auto_password, nickname)
        # Initialize scheduler for new identity
        _initialize_processes(auto_password)
        return redirect('/')
    else:
        return redirect('/identity-setup-required')



@app.route('/delete-identity')
def delete_identity_route():
    """Delete Briar identity completely and redirect to create page."""
    # Stop scheduler if running
    _cleanup_scheduler()
    delete_identity()  # Kill process and remove all data
    # Redirect to main route which will show create identity page
    return redirect('/')

@app.route('/get-contacts', methods=['GET'])
def get_contacts_route():
    """Get list of all contacts."""
    contacts = get_contacts()
    
    if contacts is not None:
        return jsonify({'success': True, 'contacts': contacts})
    else:
        return jsonify({'success': False, 'error': 'Failed to get contacts'})

@app.route('/add-contact', methods=['POST'])
def add_contact_route():
    """Add a new contact using their Briar invitation link."""
    # Check if Briar identity is running
    is_running, error_response = _check_identity_running()
    if not is_running:
        return error_response
    
    briar_link = request.form.get('briar_link', '').strip()
    alias = request.form.get('alias', '').strip()
    
    if not briar_link or not alias:
        return jsonify({'success': False, 'error': 'Both Briar link and alias are required'})
    
    if not briar_link.startswith('briar://'):
        return jsonify({'success': False, 'error': 'Invalid Briar link format'})
    
    result = add_contact(briar_link, alias)
    
    if result:
        return jsonify({'success': True, 'data': result})
    else:
        return jsonify({'success': False, 'error': 'Failed to add contact'})

@app.route('/remove-contacts', methods=['POST'])
def remove_contacts_route():
    """Remove selected contacts."""
    # Check if Briar identity is running
    is_running, error_response = _check_identity_running()
    if not is_running:
        return error_response
    
    contact_ids = request.json.get('contact_ids', [])
    
    if not contact_ids:
        return jsonify({'success': False, 'error': 'No contacts selected'})
    
    success_count = 0
    failed_count = 0
    
    for contact_id in contact_ids:
        if remove_contact(contact_id):
            success_count += 1
        else:
            failed_count += 1
    
    if failed_count == 0:
        return jsonify({'success': True, 'message': f'Successfully removed {success_count} contacts'})
    elif success_count == 0:
        return jsonify({'success': False, 'error': f'Failed to remove all {failed_count} contacts'})
    else:
        return jsonify({'success': True, 'message': f'Removed {success_count} contacts, failed to remove {failed_count} contacts'})

@app.route('/broadcast-message', methods=['POST'])
def broadcast_message_route():
    """Send a broadcast message to all contacts (immediately or scheduled)."""
    
    # Check if Briar identity is running
    is_running, error_response = _check_identity_running()
    if not is_running:
        return error_response
    
    
    message_title = request.form.get('broadcast_title', '').strip()
    message_text = request.form.get('broadcast_message', '').strip()
    schedule_date = request.form.get('schedule_date', '').strip()
    schedule_time = request.form.get('schedule_time', '').strip()
    
    # Dead man's switch parameters
    is_dead_mans_switch = request.form.get('dead_mans_switch') == 'true'
    dms_amount = request.form.get('dms_amount', '').strip()
    dms_unit = request.form.get('dms_unit', '').strip()
    reset_word = request.form.get('reset_word', '').strip()
    
    
    if not message_title:
        return jsonify({'success': False, 'error': 'Message title is required'})
    
    if not message_text:
        return jsonify({'success': False, 'error': 'Message text is required'})
    
    # Handle dead man's switch
    if is_dead_mans_switch:
        if not dms_amount or not dms_unit or not reset_word:
            return jsonify({'success': False, 'error': 'Dead man\'s switch requires interval and reset word'})
        
        try:
            
            # Convert interval to seconds
            amount = int(dms_amount)
            if amount <= 0:
                return jsonify({'success': False, 'error': 'Interval amount must be positive'})
            
            unit_multipliers = {
                'hours': 3600,
                'days': 86400,
                'weeks': 604800,
                'months': 2629746,  # ~30.44 days
                'years': 31556952   # ~365.24 days
            }
            
            if dms_unit not in unit_multipliers:
                return jsonify({'success': False, 'error': 'Invalid time unit'})
            
            interval_seconds = amount * unit_multipliers[dms_unit]
            
            # Create dead man's switch
            dms = get_dead_mans_switch()
            success = dms.schedule_dead_mans_switch(
                interval_seconds=interval_seconds,
                main_message=message_text,
                reset_word=reset_word,
                contact_id=None  # Broadcast to all
            )
            
            if not success:
                return jsonify({'success': False, 'error': 'Failed to create dead man\'s switch'})
            
            trigger_time = datetime.now() + timedelta(seconds=interval_seconds)
            
            return jsonify({
                'success': True,
                'scheduled': True,
                'dead_mans_switch': True,
                'scheduled_time': trigger_time.strftime('%Y-%m-%d %H:%M'),
                'reset_word': reset_word,
                'message': f'Dead man\'s switch created, triggering at {trigger_time.strftime("%Y-%m-%d %H:%M")}'
            })
            
        except ValueError as e:
            return jsonify({'success': False, 'error': f'Invalid interval: {e}'})
        except Exception as e:
            return jsonify({'success': False, 'error': f'Failed to create dead man\'s switch: {e}'})
    
    # Check if scheduling is requested
    elif schedule_date and schedule_time:
        try:
            
            # Parse the scheduled datetime
            datetime_string = f"{schedule_date}T{schedule_time}"
            scheduled_datetime = datetime.fromisoformat(datetime_string)
            
            # Validate future time
            current_time = datetime.now()
            time_diff_seconds = (scheduled_datetime - current_time).total_seconds()
            
            if scheduled_datetime <= current_time:
                return jsonify({'success': False, 'error': 'Scheduled time must be in the future'})
            
            # Get scheduler
            scheduler = get_scheduler()
            
            # Schedule the message
            message_id = scheduler.add_message(
                title=message_title,
                content=message_text,
                scheduled_time=scheduled_datetime,
                recipients=None,  # Broadcast to all
                json_payload=False
            )
            
            return jsonify({
                'success': True,
                'scheduled': True,
                'message_id': message_id,
                'scheduled_time': scheduled_datetime.strftime('%Y-%m-%d %H:%M'),
                'message': f'Message scheduled for {scheduled_datetime.strftime("%Y-%m-%d %H:%M")}'
            })
            
        except ValueError as e:
            return jsonify({'success': False, 'error': f'Invalid date/time format: {e}'})
        except Exception as e:
            return jsonify({'success': False, 'error': f'Failed to schedule message: {e}'})
    
    else:
        # Immediate broadcast with proper formatting
        import time
        timestamp = int(time.time())
        formatted_message = f"{message_title}\n\n{message_text}\n\nSent: {timestamp}"
        result = broadcast_message(formatted_message)
        
        if result['success']:
            return jsonify({
                'success': True,
                'scheduled': False,
                'total_contacts': result['total_contacts'],
                'successful': result['successful'],
                'failed': result['failed'],
                'message': f'Broadcast sent to {result["successful"]} of {result["total_contacts"]} contacts'
            })
        else:
            return jsonify({'success': False, 'error': result.get('error', 'Failed to broadcast message')})

@app.route('/contact-status')
def contact_status():
    """Get current contact status for auto-refresh."""
    contact_info = get_contact_info()
    if contact_info:
        return jsonify({
            'success': True,
            'total_contacts': contact_info['total_contacts'],
            'online_contacts': contact_info['online_contacts'],
            'contact_display': f"Contacts: {contact_info['online_contacts']}/{contact_info['total_contacts']} online"
        })
    else:
        return jsonify({
            'success': False,
            'total_contacts': 0,
            'online_contacts': 0,
            'contact_display': "Contacts: 0/0 online"
        })

@app.route('/qr-code')
def qr_code():
    """Generate QR code for identity."""
    invite_link = get_identity_invite_link()
    if not invite_link:
        return jsonify({'success': False, 'error': 'No identity available'})
    
    try:
        import qrcode
        import io
        import base64
        
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(invite_link)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Convert to base64
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        img_str = base64.b64encode(buffer.getvalue()).decode()
        
        return jsonify({
            'success': True,
            'qr_data': f'data:image/png;base64,{img_str}'
        })
    except ImportError:
        return jsonify({'success': False, 'error': 'QR library not available on server'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/send', methods=['POST'])
def api_send():
    """HTTP API endpoint for CLI tool to send messages."""
    from external_client.http_handlers import handle_send_request
    
    result, status_code = handle_send_request(_check_identity_running)
    return jsonify(result), status_code

@app.route('/get-scheduled-messages', methods=['GET'])
def get_scheduled_messages():
    """Get list of scheduled messages from the JSON file."""
    import os
    import json
    
    # Check if Briar identity is running
    is_running, error_response = _check_identity_running()
    if not is_running:
        return error_response
    
    try:
        # Path to the scheduled messages file
        home_dir = os.path.expanduser("~")
        briar_notify_dir = os.path.join(home_dir, ".briar-notify")
        messages_file = os.path.join(briar_notify_dir, "scheduled_messages.json")
        
        if not os.path.exists(messages_file):
            return jsonify({'success': True, 'messages': []})
        
        with open(messages_file, 'r') as f:
            messages = json.load(f)
        
        return jsonify({'success': True, 'messages': messages})
        
    except Exception as e:
        return jsonify({'success': False, 'error': f'Failed to load scheduled messages: {e}'})

@app.route('/delete-scheduled-messages', methods=['POST'])
def delete_scheduled_messages():
    """Delete selected scheduled messages from the JSON file."""
    import os
    import json
    
    # Check if Briar identity is running
    is_running, error_response = _check_identity_running()
    if not is_running:
        return error_response
    
    try:
        message_ids = request.json.get('message_ids', [])
        
        if not message_ids:
            return jsonify({'success': False, 'error': 'No message IDs provided'})
        
        # Path to the scheduled messages file
        home_dir = os.path.expanduser("~")
        briar_notify_dir = os.path.join(home_dir, ".briar-notify")
        messages_file = os.path.join(briar_notify_dir, "scheduled_messages.json")
        
        if not os.path.exists(messages_file):
            return jsonify({'success': False, 'error': 'No scheduled messages file found'})
        
        # Load existing messages
        with open(messages_file, 'r') as f:
            messages = json.load(f)
        
        # Filter out the messages to delete
        original_count = len(messages)
        messages = [msg for msg in messages if msg.get('id') not in message_ids]
        deleted_count = original_count - len(messages)
        
        # Write back to file
        with open(messages_file, 'w') as f:
            json.dump(messages, f, indent=2)
        
        return jsonify({
            'success': True, 
            'deleted_count': deleted_count,
            'message': f'Successfully deleted {deleted_count} message(s)'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': f'Failed to delete scheduled messages: {e}'})

@app.route('/health')
def health():
    return {"status": "ok", "service": "briar-notify"}

if __name__ == '__main__':
    import signal
    import sys
    
    def signal_handler(signum, frame):
        _cleanup_scheduler()
        sys.exit(0)
    
    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    # Run the application
    app.run(host='0.0.0.0', port=DEFAULT_WEB_UI_PORT, debug=False)