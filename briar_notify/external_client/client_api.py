#!/usr/bin/env python3

import json
import time
import sys
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any

logger = logging.getLogger(__name__)

# Add project root to path so we can import internal_service as a package
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "briar_notify"))

try:
    from internal_service.briar_service import get_contacts, send_message, broadcast_message
    from internal_service.service_config import DEFAULT_BRIAR_PORT
    from internal_service.scheduler import get_scheduler
    from internal_service.dead_mans_switch import get_dead_mans_switch
except ImportError as e:
    sys.exit(1)


def send(title: str, content: str, recipients: Optional[List[str]] = None, 
         schedule: Optional[int] = None, json_payload: bool = False, 
         dead_mans_switch: bool = False, reset_word: str = '', 
         interval_seconds: int = 0) -> Dict[str, Any]:
    """
    Send notification to contacts.
    
    Args:
        title: Message title
        content: Message body  
        recipients: List of contact names to send to (default: None = broadcast to all)
        schedule: Unix timestamp for when to send (optional, sends immediately if None)
        json_payload: Send as JSON structure instead of plain text (default: False)
        dead_mans_switch: Enable dead man's switch functionality (default: False)
        reset_word: Word/phrase to reset or disable the switch (required if dead_mans_switch=True)
        interval_seconds: Seconds until trigger (required if dead_mans_switch=True)

    Returns:
        dict: {
            'success': bool,
            'message_id': str,
            'scheduled_for': int,
            'sent_timestamp': int,
            'recipients': list,  # names of intended recipients
            'delivered_to': list,  # contact IDs that received the message
            'failed': list  # names that failed to receive
        }
    """
    
    # Validate inputs
    if not title or not content:
        return {
            'success': False,
            'error': 'Title and content are required',
            'message_id': None,
            'scheduled_for': None,
            'sent_timestamp': None,
            'recipients': recipients or [],
            'delivered_to': [],
            'failed': []
        }
    
    # Handle dead man's switch
    if dead_mans_switch:
        if not reset_word or interval_seconds <= 0:
            return {
                'success': False,
                'error': 'Dead man\'s switch requires reset_word and positive interval_seconds',
                'message_id': None,
                'scheduled_for': None,
                'sent_timestamp': None,
                'recipients': recipients or [],
                'delivered_to': [],
                'failed': []
            }
        
        try:
            dms = get_dead_mans_switch()
            success = dms.schedule_dead_mans_switch(
                interval_seconds=interval_seconds,
                main_message=content,
                reset_word=reset_word,
                contact_id=recipients[0] if recipients and len(recipients) == 1 else None
            )
            
            if success:
                message_id = f"dms_{int(time.time())}_{hash(reset_word + content) % 10000:04d}"
                scheduled_timestamp = int(time.time()) + interval_seconds
                
                return {
                    'success': True,
                    'message_id': message_id,
                    'scheduled_for': scheduled_timestamp,
                    'sent_timestamp': None,
                    'recipients': recipients or [],
                    'delivered_to': [],
                    'failed': [],
                    'dead_mans_switch': True,
                    'reset_word': reset_word
                }
            else:
                return {
                    'success': False,
                    'error': 'Failed to schedule dead man\'s switch',
                    'message_id': None,
                    'scheduled_for': None,
                    'sent_timestamp': None,
                    'recipients': recipients or [],
                    'delivered_to': [],
                    'failed': []
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f'Dead man\'s switch failed: {str(e)}',
                'message_id': None,
                'scheduled_for': None,
                'sent_timestamp': None,
                'recipients': recipients or [],
                'delivered_to': [],
                'failed': []
            }
    
    # Validate schedule parameters
    if schedule is not None:
        current_time = int(time.time())
        if schedule <= current_time:
            return {
                'success': False,
                'error': f'Schedule time {schedule} must be in the future (current: {current_time})',
                'message_id': None,
                'scheduled_for': None,
                'sent_timestamp': None,
                'recipients': recipients or [],
                'delivered_to': [],
                'failed': []
            }
        
    
    # Format message
    if json_payload:
        # For scheduled messages, we'll add the timestamp when actually sent
        if schedule is None:
            message_text = json.dumps({
                'title': title,
                'content': content,
                'sent_timestamp': int(time.time())
            })
        else:
            # For scheduled messages, timestamp will be added when sent
            message_text = json.dumps({
                'title': title,
                'content': content,
                'sent_timestamp': None  # Will be updated when actually sent
            })
    else:
        # For immediate sending, add timestamp now
        if schedule is None:
            timestamp = int(time.time())
            message_text = f"{title}\n\n{content}\n\nSent: {timestamp}"
        else:
            # For scheduled messages, timestamp will be added when sent
            message_text = f"{title}\n\n{content}"
    
    # Generate message ID
    message_id = f"msg_{int(time.time())}_{hash(title + content) % 10000:04d}"
    
    # Handle scheduled messages
    if schedule is not None:
        try:
            # Convert unix timestamp to datetime
            schedule_datetime = datetime.fromtimestamp(schedule)
            
            scheduler = get_scheduler()
            
            scheduled_message_id = scheduler.add_message(
                title,
                content,
                schedule_datetime,
                recipients,
                json_payload
            )
            
            return {
                'success': True,
                'message_id': scheduled_message_id,
                'scheduled_for': schedule,
                'sent_timestamp': None,
                'recipients': recipients or [],
                'delivered_to': [],
                'failed': []
            }
            
        except Exception as scheduling_error:
            return {
                'success': False,
                'error': f'Scheduling failed: {str(scheduling_error)}',
                'message_id': message_id,
                'scheduled_for': None,
                'sent_timestamp': None,
                'recipients': recipients or [],
                'delivered_to': [],
                'failed': []
            }
    
    # Send immediately
    sent_timestamp = int(time.time())
    
    # Update JSON payload with actual sent timestamp
    if json_payload:
        message_data = json.loads(message_text)
        message_data['sent_timestamp'] = sent_timestamp
        message_text = json.dumps(message_data)
    
    # Add 10 second delay before sending
    time.sleep(10)
    
    try:
        if recipients is None:
            # Broadcast to all contacts
            result = broadcast_message(message_text, DEFAULT_BRIAR_PORT)
            
            if result.get('success'):
                # Get contact names for response
                contacts = get_contacts(DEFAULT_BRIAR_PORT) or []
                contact_names = [contact.get('author', {}).get('name', f"Contact_{contact.get('contactId')}") 
                               for contact in contacts]
                delivered_contact_ids = [contact.get('contactId') for contact in contacts]
                
                return {
                    'success': True,
                    'message_id': message_id,
                    'scheduled_for': None,
                    'sent_timestamp': sent_timestamp,
                    'recipients': contact_names,
                    'delivered_to': delivered_contact_ids,
                    'failed': []
                }
            else:
                return {
                    'success': False,
                    'error': result.get('error', 'Broadcast failed'),
                    'message_id': message_id,
                    'scheduled_for': None,
                    'sent_timestamp': None,
                    'recipients': [],
                    'delivered_to': [],
                    'failed': []
                }
        
        else:
            # Send to specific recipients
            contacts = get_contacts(DEFAULT_BRIAR_PORT)
            if not contacts:
                return {
                    'success': False,
                    'error': 'No contacts found or failed to get contacts',
                    'message_id': message_id,
                    'scheduled_for': None,
                    'sent_timestamp': None,
                    'recipients': recipients,
                    'delivered_to': [],
                    'failed': recipients
                }
            
            # Build name to contact mapping
            name_to_contact = {}
            for contact in contacts:
                name = contact.get('author', {}).get('name')
                if name:
                    name_to_contact[name] = contact
            
            delivered_to = []
            failed = []
            
            for recipient_name in recipients:
                if recipient_name in name_to_contact:
                    contact = name_to_contact[recipient_name]
                    contact_id = contact.get('contactId')
                    
                    result = send_message(contact_id, message_text, DEFAULT_BRIAR_PORT)
                    if result:
                        delivered_to.append(contact_id)
                    else:
                        failed.append(recipient_name)
                    # Add delay between individual sends
                    time.sleep(10)
                else:
                    failed.append(recipient_name)
            
            success = len(failed) == 0
            
            return {
                'success': success,
                'message_id': message_id,
                'scheduled_for': None,
                'sent_timestamp': sent_timestamp if success else None,
                'recipients': recipients,
                'delivered_to': delivered_to,
                'failed': failed
            }
    
    except Exception as e:
        return {
            'success': False,
            'error': f'Send failed: {str(e)}',
            'message_id': message_id,
            'scheduled_for': None,
            'sent_timestamp': None,
            'recipients': recipients or [],
            'delivered_to': [],
            'failed': recipients or []
        }


def _send_immediate_message(message_text: str, recipients: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Internal function to send message immediately (used by scheduler).
    
    Args:
        message_text: Formatted message text (plain or JSON)
        recipients: List of contact names (None = broadcast to all)
        
    Returns:
        dict: Delivery results
    """
    try:
        if recipients is None:
            # Broadcast to all contacts
            result = broadcast_message(message_text, DEFAULT_BRIAR_PORT)
            return result
        else:
            # Send to specific recipients
            contacts = get_contacts(DEFAULT_BRIAR_PORT)
            if not contacts:
                return {'success': False, 'error': 'No contacts found'}
            
            # Build name to contact mapping
            name_to_contact = {}
            for contact in contacts:
                name = contact.get('author', {}).get('name')
                if name:
                    name_to_contact[name] = contact
            
            delivered_count = 0
            for recipient_name in recipients:
                if recipient_name in name_to_contact:
                    contact = name_to_contact[recipient_name]
                    contact_id = contact.get('contactId')
                    
                    result = send_message(contact_id, message_text, DEFAULT_BRIAR_PORT)
                    if result:
                        delivered_count += 1
            
            return {
                'success': delivered_count > 0,
                'delivered_count': delivered_count,
                'total_recipients': len(recipients)
            }
    
    except Exception as e:
        return {'success': False, 'error': str(e)}

