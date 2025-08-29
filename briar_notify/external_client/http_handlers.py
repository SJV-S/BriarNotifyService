#!/usr/bin/env python3

"""
HTTP API interface for external clients.
Provides Flask endpoint handlers for the Briar Notify Service.
"""

import sys
from pathlib import Path
from flask import request, jsonify

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "briar_notify"))

from external_client.client_api import send


def handle_send_request(check_identity_running_func):
    """
    Handle HTTP API send request.
    
    Args:
        check_identity_running_func: Function to check if Briar identity is running
        
    Returns:
        tuple: (json_response, http_status_code)
    """
    try:
        # Check if Briar identity is running
        is_running, error_response = check_identity_running_func()
        if not is_running:
            return {'success': False, 'error': 'Briar identity not running'}, 400
        
        # Parse request data
        data = request.get_json() or {}
        
        title = data.get('title', '').strip()
        content = data.get('content', '').strip()
        recipients = data.get('recipients')  # List of names or None for broadcast
        schedule = data.get('schedule')  # Unix timestamp or None for immediate
        json_payload = data.get('json_payload', False)
        
        if not title or not content:
            return {'success': False, 'error': 'Title and content are required'}, 400
        
        # Call the send function
        result = send(title, content, recipients, schedule, json_payload)
        
        # Return appropriate HTTP status code
        if result['success']:
            return result, 200
        else:
            return result, 400
            
    except Exception as e:
        return {'success': False, 'error': f'API error: {str(e)}'}, 500