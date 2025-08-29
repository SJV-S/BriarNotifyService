#!/usr/bin/env python3

import json
import threading
import time
import sys
from datetime import datetime
from typing import List, Dict, Any, Optional
from internal_service.service_config import BRIAR_NOTIFY_DIR, DEFAULT_BRIAR_PORT
from internal_service.briar_service import get_contacts, send_message, broadcast_message



class MessageScheduler:
    def __init__(self):
        self.running = False
        self.thread = None
        self.wake_event = threading.Event()
        self.messages_path = BRIAR_NOTIFY_DIR / 'scheduled_messages.json'
        self.default_sleep_seconds = 60
        BRIAR_NOTIFY_DIR.mkdir(parents=True, exist_ok=True)
    
    
    def start(self):
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._scheduler_loop, daemon=True)
        self.thread.start()
    
    def stop(self):
        if not self.running:
            return
        self.running = False
        self.wake_event.set()
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=5)
    
    def add_message(self, title: str, content: str, scheduled_time: datetime,
                   recipients: Optional[List[str]] = None, json_payload: bool = False,
                   dead_mans_switch: bool = False, reset_word: str = '',
                   original_interval_seconds: int = 0) -> str:
        
        
        message_id = f"msg_{int(time.time())}_{hash(title + content) % 10000:04d}"
        timestamp = int(scheduled_time.timestamp())
        current_time = int(time.time())
        
        
        if timestamp <= current_time:
        
        message_data = {
            'id': message_id,
            'title': title,
            'content': content,
            'scheduled_timestamp': timestamp,
            'recipients': recipients,
            'json_payload': json_payload,
            'dead_mans_switch': dead_mans_switch,
            'reset_word': reset_word,
            'original_interval_seconds': original_interval_seconds
        }
        
        # Store message in single unencrypted database
        try:
            with open(self.messages_path, 'r') as f:
                messages = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            messages = []
        
        messages.append(message_data)
        
        with open(self.messages_path, 'w') as f:
            json.dump(messages, f, indent=2)
        
        self.wake_event.set()
        return message_id
    
    def _scheduler_loop(self):
        while self.running:
            try:
                self._process_due_messages()
                sleep_time = self._get_sleep_time()
                self.wake_event.wait(sleep_time)
                self.wake_event.clear()
            except Exception as e:
                time.sleep(self.default_sleep_seconds)
    
    def _process_due_messages(self):
        current_time = int(time.time())
        
        # Load messages from single database
        try:
            with open(self.messages_path, 'r') as f:
                messages = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return
        
        if not messages:
            return
        
        due_messages = []
        remaining_messages = []
        
        for msg in messages:
            msg_time = msg['scheduled_timestamp']
            msg_id = msg.get('id', 'unknown')
            msg_title = msg.get('title', 'no title')
            reset_word = msg.get('reset_word', '')
            
            if msg_time <= current_time:
                due_messages.append(msg)
                self._send_message(msg)
            else:
                remaining_messages.append(msg)
        
        
        # Update storage if messages were processed
        if len(remaining_messages) != len(messages):
            with open(self.messages_path, 'w') as f:
                json.dump(remaining_messages, f, indent=2)
        else:
    
    def _send_message(self, msg: Dict[str, Any]):
        try:
            if msg.get('json_payload'):
                message_text = json.dumps({
                    'title': msg['title'],
                    'content': msg['content'],
                    'sent_timestamp': int(time.time())
                })
            else:
                sent_timestamp = int(time.time())
                
                # Build message with timestamps
                message_text = f"{msg['title']}\n\n{msg['content']}\n\nSent: {sent_timestamp}"
            
            # Use imported functions
            
            recipients = msg.get('recipients')
            if recipients is None:
                # Broadcast to all contacts
                result = broadcast_message(message_text, DEFAULT_BRIAR_PORT)
                if result.get('success'):
                else:
            else:
                # Send to specific recipients
                contacts = get_contacts(DEFAULT_BRIAR_PORT)
                if not contacts:
                    return
                
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
                
                if delivered_count > 0:
                else:
                    
        except Exception as e:
    
    def _get_sleep_time(self) -> float:
        try:
            with open(self.messages_path, 'r') as f:
                messages = json.load(f)
            
            current_time = int(time.time())
            future_timestamps = [msg['scheduled_timestamp'] for msg in messages if msg['scheduled_timestamp'] > current_time]
            
            if future_timestamps:
                return max(1, min(min(future_timestamps) - current_time, 300))
            return self.default_sleep_seconds
        except (FileNotFoundError, json.JSONDecodeError):
            return self.default_sleep_seconds
    
    def delete_messages_by_reset_word(self, reset_word: str) -> bool:
        """Delete all messages with the specified reset word.
        
        Args:
            reset_word: Reset word to match (case-insensitive)
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            
            try:
                with open(self.messages_path, 'r') as f:
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
            with open(self.messages_path, 'w') as f:
                json.dump(remaining_messages, f, indent=2)
            
            
            # Wake up the scheduler to recalculate sleep time
            self.wake_event.set()
            
            return True
            
        except Exception as e:
            return False


# Global instance
_scheduler_instance = None
_scheduler_lock = threading.Lock()

def get_scheduler() -> MessageScheduler:
    global _scheduler_instance
    with _scheduler_lock:
        if _scheduler_instance is None:
            _scheduler_instance = MessageScheduler()
            _scheduler_instance.start()
        return _scheduler_instance

def stop_scheduler():
    global _scheduler_instance
    with _scheduler_lock:
        if _scheduler_instance is not None:
            _scheduler_instance.stop()
            _scheduler_instance = None