
import requests
import subprocess
import time
import socket
from internal_service.service_config import BRIAR_DIR, BRIAR_JAR_PATH, DEFAULT_BRIAR_PORT, auth_manager, BRIAR_NOTIFY_DIR, JAVA_PATH
from internal_service.password_manager import password_manager


def get_identity_invite_link():
    headers = auth_manager.get_auth_headers()
    if not headers:
        return None
    
    try:
        response = requests.get(
            f'http://localhost:{DEFAULT_BRIAR_PORT}/v1/contacts/add/link',
            headers=headers,
            timeout=5
        )
        
        if response.status_code == 200:
            data = response.json()
            return data.get('link')
    except requests.exceptions.ConnectionError:
        # Briar not running - return None so dashboard can redirect to start page
        return None
    except Exception:
        # Any other error - return None 
        return None
    
    return None

def identity_running(port=DEFAULT_BRIAR_PORT):
    # True if Briar identity is running, API is responsive, and crypto password is set

    # Check auth token
    if not auth_manager.has_token():
        return False

    # Check if encryption password is available
    if password_manager.identity_password is None:
        return False

    # Test briar headless API
    try:
        headers = auth_manager.get_auth_headers()
        response = requests.get(
            f'http://localhost:{port}/v1/contacts/add/link',
            headers=headers,
            timeout=2
        )
        return response.status_code == 200
    except Exception:
        return False


def is_port_listening(port):
    """Check if a service is listening on a specific port.
    
    Args:
        port: Port number to check
    
    Returns:
        bool: True if something is listening on the port
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(1)  # 1 second timeout
    
    try:
        result = sock.connect_ex(('localhost', port))
        return result == 0  # 0 means connection successful
    except Exception:
        return False
    finally:
        sock.close()

def start_briar_process(input_data, port=DEFAULT_BRIAR_PORT):
    """Start Briar headless process with given input.
    
    Args:
        input_data: String to pipe to Briar (e.g. nickname, password for new identity 
                   or just password for existing identity)
        port: Port for Briar API to listen on (default from config)
    
    Returns:
        subprocess.Popen: The started process
    """
    # Use Popen with stdin to securely pass password without exposing it in process list
    process = subprocess.Popen(
        [JAVA_PATH, '-jar', BRIAR_JAR_PATH, '--port', str(port)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    # Send the input data to stdin and close it
    process.stdin.write(input_data + '\n')
    process.stdin.close()
    
    return process

def wait_for_briar_ready(timeout_seconds=15, port=DEFAULT_BRIAR_PORT):
    """Poll for Briar API to be fully ready.
    
    Args:
        timeout_seconds: How long to wait before giving up
        port: Briar API port to check
        
    Returns:
        bool: True if Briar API is ready, False if timeout
    """
    time.sleep(1)  # Initial wait
    for i in range(timeout_seconds):
        time.sleep(1)
        if identity_running(port):
            return True
    return False

def logout_identity(port=DEFAULT_BRIAR_PORT):
    """Logout from Briar identity by invalidating token and killing process.
    
    Args:
        port: Briar API port (default 7000)
        
    Returns:
        bool: True if logout successful, False otherwise
    """
    logout_success = False
    
    # Try to logout via API first if token exists
    headers = auth_manager.get_auth_headers()
    if headers:
        try:
            response = requests.post(
                f'http://localhost:{port}/v1/logout',
                headers=headers,
                timeout=5
            )
            logout_success = response.status_code == 204
        except Exception:
            pass  # Continue with process killing even if API logout fails
    
    # Kill Briar process
    try:
        # Kill all Java processes running briar-headless.jar
        subprocess.run(['pkill', '-9', '-f', 'briar-headless'], check=False)
        # Also kill any Tor processes started by Briar
        subprocess.run(['pkill', '-9', '-f', 'tor.*briar'], check=False)
        
        return True
    except Exception:
        return logout_success  # Return API logout result if process killing fails

def get_contacts(port=DEFAULT_BRIAR_PORT):
    """Get list of all contacts.
    
    Args:
        port: Briar API port (default 7000)
        
    Returns:
        list: List of contact dictionaries
        None: If operation failed
    """
    headers = auth_manager.get_auth_headers()
    if not headers:
        return None
    
    try:
        response = requests.get(
            f'http://localhost:{port}/v1/contacts',
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            return None
    except Exception:
        return None

def get_contact_info(port=DEFAULT_BRIAR_PORT):
    """Get comprehensive contact information including counts and status.
    
    Args:
        port: Briar API port (default 7000)
        
    Returns:
        dict: Contact information with structure:
            {
                'success': bool,
                'contacts': list,  # Full contact list from API
                'total_contacts': int,
                'online_contacts': int,
                'offline_contacts': int,
                'unread_total': int
            }
        None: If operation failed
    """
    contacts = get_contacts(port)
    
    if contacts is None:
        return None
    
    online_count = sum(1 for contact in contacts if contact.get('connected', False))
    offline_count = len(contacts) - online_count
    unread_total = sum(contact.get('unreadCount', 0) for contact in contacts)
    
    return {
        'success': True,
        'contacts': contacts,
        'total_contacts': len(contacts),
        'online_contacts': online_count,
        'offline_contacts': offline_count,
        'unread_total': unread_total
    }

def remove_contact(contact_id, port=DEFAULT_BRIAR_PORT):
    """Remove a contact by ID.
    
    Args:
        contact_id: The contact ID to remove
        port: Briar API port (default 7000)
        
    Returns:
        bool: True if successful, False if failed
    """
    headers = auth_manager.get_auth_headers()
    if not headers:
        return False
    
    try:
        response = requests.delete(
            f'http://localhost:{port}/v1/contacts/{contact_id}',
            headers=headers,
            timeout=10
        )
        
        return response.status_code == 204 or response.status_code == 200
    except Exception:
        return False

def send_message(contact_id, message_text, port=DEFAULT_BRIAR_PORT):
    """Send a message to a specific contact.
    
    Args:
        contact_id: The contact ID to send message to
        message_text: The message text to send
        port: Briar API port (default 7000)
        
    Returns:
        dict: Response from API with message details
        None: If operation failed
    """
    headers = auth_manager.get_auth_headers()
    if not headers:
        return None
    
    # Add content-type to auth headers
    headers['Content-Type'] = 'application/json'
    
    try:
        response = requests.post(
            f'http://localhost:{port}/v1/messages/{contact_id}',
            headers=headers,
            json={
                'contactId': contact_id,
                'text': message_text
            },
            timeout=10
        )
        
        if response.status_code == 201 or response.status_code == 200:
            return response.json()
        else:
            return None
    except Exception:
        return None

def broadcast_message(message_text, port=DEFAULT_BRIAR_PORT):
    """Send a message to all connected contacts (broadcast).
    
    Args:
        message_text: The message text to broadcast
        port: Briar API port (default 7000)
        
    Returns:
        dict: Summary of broadcast results
    """
    contacts = get_contacts(port)
    if not contacts:
        return {'success': False, 'error': 'No contacts found or failed to get contacts'}
    
    results = {
        'total_contacts': len(contacts),
        'successful': 0,
        'failed': 0,
        'results': []
    }
    
    for contact in contacts:
        contact_id = contact.get('contactId')
        alias = contact.get('alias', f'Contact {contact_id}')
        
        result = send_message(contact_id, message_text, port)
        if result:
            results['successful'] += 1
            results['results'].append({
                'contact_id': contact_id,
                'alias': alias,
                'status': 'success'
            })
        else:
            results['failed'] += 1
            results['results'].append({
                'contact_id': contact_id,
                'alias': alias,
                'status': 'failed'
            })
    
    results['success'] = results['failed'] == 0
    return results

def add_contact(briar_link, alias, port=DEFAULT_BRIAR_PORT):
    """Add a contact using their Briar invitation link.
    
    Args:
        briar_link: The Briar invitation link (briar://...)
        alias: Display name for the contact
        port: Briar API port (default 7000)
        
    Returns:
        dict: Response from API with pendingContactId, alias, timestamp
        None: If operation failed
    """
    headers = auth_manager.get_auth_headers()
    if not headers:
        return None
    
    # Add content-type to auth headers
    headers['Content-Type'] = 'application/json'
    
    try:
        response = requests.post(
            f'http://localhost:{port}/v1/contacts/add/pending',
            headers=headers,
            json={
                'link': briar_link,
                'alias': alias
            },
            timeout=10
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            return None
    except Exception:
        return None

def get_identity_name():
    """Get the identity name from the identity.json file."""
    import json
    
    identity_file = BRIAR_NOTIFY_DIR / "identity.json"
    if not identity_file.exists():
        return None
    
    try:
        data = json.loads(identity_file.read_text())
        return data.get("nickname")
    except Exception:
        return None

def delete_identity():
    # Delete .briar directory
    try:
        # Kill all Briar-related processes (shell and java)
        subprocess.run(['pkill', '-f', 'briar-headless.jar'], check=False)
        subprocess.run(['pkill', '-f', 'echo.*briar-headless'], check=False)
        
        # Give processes time to die
        time.sleep(1)
        
        # Remove entire Briar directory
        subprocess.run(['rm', '-rf', str(BRIAR_DIR)], check=False)
        
        return True
    except Exception:
        return False