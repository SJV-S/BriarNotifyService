#!/usr/bin/env python3

import json
import sys
import time
from datetime import datetime, timedelta
from typing import Optional
from internal_service.scheduler import get_scheduler
from internal_service.briar_service import send_message, get_contacts
from internal_service.service_config import BRIAR_NOTIFY_DIR


class DeadMansSwitch:
    def __init__(self):
        self.scheduler = get_scheduler()
    
    def schedule_dead_mans_switch(self, interval_seconds: int, main_message: str, 
                                 reset_word: str, contact_id: Optional[str] = None) -> bool:
        """Schedule a dead man's switch with 3 messages: main, 24hr warning, 2hr warning.
        
        Args:
            interval_seconds: Time in seconds until the main message is sent
            main_message: The main dead man's switch message content
            reset_word: Case-insensitive word/phrase to reset or disable the switch
            contact_id: Specific contact to send to, or None for broadcast
            
        Returns:
            bool: True if successfully scheduled, False otherwise
        """
        
        try:
            current_time = datetime.now()
            
            # Calculate schedule times
            main_time = current_time + timedelta(seconds=interval_seconds)
            warning_24h_time = main_time - timedelta(hours=24)
            warning_2h_time = main_time - timedelta(hours=2)
            
            # Determine recipients
            recipients = [contact_id] if contact_id else None
            
            # Schedule 24-hour warning (only if interval > 24 hours)
            if interval_seconds > 24 * 3600:
                warning_24h_id = self.scheduler.add_message(
                    title="Dead Man's Switch - 24 Hour Warning",
                    content="This is a 24-hour warning. The dead man's switch will trigger in 24 hours unless reset with the correct word.",
                    scheduled_time=warning_24h_time,
                    recipients=recipients,
                    dead_mans_switch=True,
                    reset_word=reset_word.lower(),
                    original_interval_seconds=interval_seconds
                )
            
            # Schedule 2-hour warning (only if interval > 2 hours)
            if interval_seconds > 2 * 3600:
                warning_2h_id = self.scheduler.add_message(
                    title="Dead Man's Switch - 2 Hour Warning",
                    content="This is a 2-hour warning. The dead man's switch will trigger in 2 hours unless reset with the correct word.",
                    scheduled_time=warning_2h_time,
                    recipients=recipients,
                    dead_mans_switch=True,
                    reset_word=reset_word.lower(),
                    original_interval_seconds=interval_seconds
                )
            
            # Schedule main message
            main_id = self.scheduler.add_message(
                title="Dead Man's Switch - Triggered",
                content=main_message,
                scheduled_time=main_time,
                recipients=recipients,
                dead_mans_switch=True,
                reset_word=reset_word.lower(),
                original_interval_seconds=interval_seconds
            )
            return True
            
        except Exception as e:
            return False
    
    def process_incoming_message(self, contact_id: str, message_text: str, full_message_data: dict):
        """Process incoming message to check for reset word or disable command.
        
        Args:
            contact_id: ID of the contact who sent the message
            message_text: The text content of the message
            full_message_data: Complete message data for debugging
        """
        
        if not message_text:
            return
        
        message_lower = message_text.lower().strip()
        
        # Get all unique reset words from scheduled messages
        try:
            messages_path = BRIAR_NOTIFY_DIR / 'scheduled_messages.json'
            
            try:
                with open(messages_path, 'r') as f:
                    messages = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError):
                return
            
            # Get all unique reset words from active dead man's switch messages
            active_reset_words = {}
            for msg in messages:
                if msg.get('dead_mans_switch') and msg.get('reset_word'):
                    reset_word = msg['reset_word'].lower()
                    if reset_word not in active_reset_words:
                        active_reset_words[reset_word] = msg.get('original_interval_seconds', 0)
            
            if not active_reset_words:
                return
            
            # Check if incoming message contains any active reset words
            found_reset_word = None
            original_interval = 0
            for reset_word, interval in active_reset_words.items():
                if reset_word in message_lower:
                    found_reset_word = reset_word
                    original_interval = interval
                    break
            
            if not found_reset_word:
                return
            
            # Process the single matching reset word
            
            # Check if this is a disable command (reset word + "end")
            if "end" in message_lower:
                success = self._disable_dead_mans_switch(found_reset_word, contact_id)
                if success:
                    self._send_confirmation(contact_id, "Dead man's switch has been permanently disabled.")
                else:
                    self._send_confirmation(contact_id, "Failed to disable dead man's switch.")
            else:
                success = self._reset_dead_mans_switch(found_reset_word, original_interval, contact_id)
                if success:
                    self._send_confirmation(contact_id, "Dead man's switch has been reset and timer restarted.")
                else:
                    self._send_confirmation(contact_id, "Failed to reset dead man's switch.")
                        
        except Exception as e:
            pass
    
    def _disable_dead_mans_switch(self, reset_word: str, contact_id: str) -> bool:
        """Permanently disable a dead man's switch by deleting all associated messages.
        
        Args:
            reset_word: The reset word to match (case-insensitive)
            contact_id: Contact who requested the disable
            
        Returns:
            bool: True if successful, False otherwise
        """
        
        return self._delete_messages_by_reset_word(reset_word)
    
    def _reset_dead_mans_switch(self, reset_word: str, original_interval_seconds: int, contact_id: str) -> bool:
        """Reset a dead man's switch by deleting existing messages and rescheduling new ones.
        
        Args:
            reset_word: The reset word to match (case-insensitive)
            original_interval_seconds: Original interval to use for rescheduling
            contact_id: Contact who requested the reset
            
        Returns:
            bool: True if successful, False otherwise
        """
        
        # First, get the original message content before deleting
        original_content = self._get_main_message_content(reset_word)
        if not original_content:
            return False
        
        # Delete existing messages
        if not self._delete_messages_by_reset_word(reset_word):
            return False
        
        # Reschedule with new timing
        return self.schedule_dead_mans_switch(
            interval_seconds=original_interval_seconds,
            main_message=original_content,
            reset_word=reset_word,
            contact_id=contact_id
        )
    
    def _get_main_message_content(self, reset_word: str) -> Optional[str]:
        """Get the content of the main dead man's switch message.
        
        Args:
            reset_word: Reset word to match
            
        Returns:
            str: Main message content, or None if not found
        """
        try:
            messages_path = BRIAR_NOTIFY_DIR / 'scheduled_messages.json'
            
            with open(messages_path, 'r') as f:
                messages = json.load(f)
            
            for msg in messages:
                if (msg.get('dead_mans_switch') and 
                    msg.get('reset_word', '').lower() == reset_word.lower() and
                    msg.get('title', '').startswith('Dead Man\'s Switch - Triggered')):
                    return msg.get('content', '')
            
            return None
            
        except Exception as e:
            return None
    
    def _delete_messages_by_reset_word(self, reset_word: str) -> bool:
        """Delete all messages with the specified reset word.
        
        Args:
            reset_word: Reset word to match (case-insensitive)
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            messages_path = BRIAR_NOTIFY_DIR / 'scheduled_messages.json'
            
            try:
                with open(messages_path, 'r') as f:
                    messages = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError):
                return True
            
            # Filter out messages with matching reset word
            original_count = len(messages)
            remaining_messages = []
            deleted_count = 0
            
            for msg in messages:
                if (msg.get('dead_mans_switch') and 
                    msg.get('reset_word', '').lower() == reset_word.lower()):
                    deleted_count += 1
                else:
                    remaining_messages.append(msg)
            
            # Save updated messages
            with open(messages_path, 'w') as f:
                json.dump(remaining_messages, f, indent=2)
            
            
            return True
            
        except Exception as e:
            return False
    
    def _send_confirmation(self, contact_id: str, message: str):
        """Send a confirmation message to the specified contact.
        
        Args:
            contact_id: Contact ID to send confirmation to
            message: Confirmation message text
        """
        try:
            # Add 1 second delay before responding
            time.sleep(1)
            result = send_message(contact_id, message)
            if result:
                pass
        except Exception as e:
            pass


# Global instance
_dms_instance = None

def get_dead_mans_switch() -> DeadMansSwitch:
    """Get the global dead man's switch instance."""
    global _dms_instance
    if _dms_instance is None:
        _dms_instance = DeadMansSwitch()
    return _dms_instance
