// Identity Management - toggleIdentity function removed since show button was removed

function copyIdentity() {
    const identityElement = document.getElementById('identityDisplay');
    const identity = identityElement ? identityElement.textContent.trim() : '';
    
    if (!identity) {
        showToastFeedback('No identity found to copy', true);
        return;
    }

    const textArea = document.createElement('textarea');
    textArea.value = identity;
    textArea.style.position = 'absolute';
    textArea.style.left = '-9999px';
    textArea.style.top = '0';
    textArea.readOnly = false;
    
    document.body.appendChild(textArea);
    textArea.focus();
    textArea.select();
    textArea.setSelectionRange(0, identity.length);
    
    try {
        const successful = document.execCommand('copy');
        if (successful) {
            showCopyFeedback();
        } else {
            throw new Error('execCommand failed');
        }
    } catch (err) {
        showToastFeedback('Copy failed', true);
    } finally {
        document.body.removeChild(textArea);
    }
}

function showToastFeedback(message, isError = false) {
    // Create feedback element
    const feedback = document.createElement('div');
    feedback.textContent = message;
    const backgroundColor = isError ? '#ef4444' : '#3b82f6';
    feedback.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: ${backgroundColor};
        color: white;
        padding: 12px 24px;
        border-radius: 4px;
        font-weight: 500;
        z-index: 10000;
        animation: slideIn 0.3s ease;
    `;
    document.body.appendChild(feedback);
    
    // Remove after 4 seconds
    setTimeout(() => {
        feedback.remove();
    }, 4000);
}

function showCopyFeedback() {
    showToastFeedback('Copied to clipboard');
}

function showQRModal() {
    const modal = document.getElementById('qrModal');
    const container = document.getElementById('qrCodeContainer');
    
    modal.style.display = 'block';
    container.innerHTML = '<p>Generating QR code...</p>';
    
    fetch('/qr-code')
    .then(response => response.json())
    .then(data => {
        container.innerHTML = '';
        if (data.success) {
            const img = document.createElement('img');
            img.src = data.qr_data;
            img.style.cssText = 'max-width: 100%; height: auto;';
            container.appendChild(img);
        } else {
            container.innerHTML = '<p>QR code generation failed</p>';
        }
    })
    .catch(error => {
        container.innerHTML = '<p>QR code generation failed</p>';
    });
}

function hideQRModal() {
    document.getElementById('qrModal').style.display = 'none';
}

// Modal Management
function showAddContactModal() {
    document.getElementById('addContactModal').style.display = 'block';
    document.getElementById('addContactResult').style.display = 'none';
    document.getElementById('addContactForm').reset();
}

function hideAddContactModal() {
    document.getElementById('addContactModal').style.display = 'none';
}

function showListContactsModal() {
    document.getElementById('listContactsModal').style.display = 'block';
    document.getElementById('contactsLoading').style.display = 'block';
    document.getElementById('contactsList').style.display = 'none';
    loadContacts();
}

function hideListContactsModal() {
    document.getElementById('listContactsModal').style.display = 'none';
}

function showBroadcastModal() {
    document.getElementById('broadcastModal').style.display = 'block';
    document.getElementById('broadcastResult').style.display = 'none';
    document.getElementById('broadcastForm').reset();
}

function hideBroadcastModal() {
    document.getElementById('broadcastModal').style.display = 'none';
}

function showScheduleModal() {
    document.getElementById('scheduleModal').style.display = 'block';
    document.getElementById('scheduleLoading').style.display = 'block';
    document.getElementById('scheduleList').style.display = 'none';
    
    // Clear any previous selections
    selectedMessages.clear();
    updateDeleteButton();
    
    // Update hint text based on device type
    updateScheduleHintText();
    
    loadScheduledMessages();
}

function isMobileDevice() {
    return /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent) || 
           ('ontouchstart' in window) || 
           (navigator.maxTouchPoints > 0);
}

function updateScheduleHintText() {
    const hintElement = document.getElementById('scheduleHint');
    if (hintElement) {
        if (isMobileDevice()) {
            hintElement.textContent = 'Tap icon to display full message.';
        } else {
            hintElement.textContent = 'Hover over icon to display full message.';
        }
    }
}

function hideScheduleModal() {
    document.getElementById('scheduleModal').style.display = 'none';
}

function loadScheduledMessages() {
    fetch('/get-scheduled-messages')
    .then(response => response.json())
    .then(data => {
        document.getElementById('scheduleLoading').style.display = 'none';
        
        if (data.success && data.messages.length > 0) {
            displayScheduledMessages(data.messages);
            document.getElementById('scheduleList').style.display = 'block';
        } else {
            document.getElementById('scheduleContainer').innerHTML = '<p>No scheduled messages found.</p>';
            document.getElementById('scheduleList').style.display = 'block';
        }
    })
    .catch(error => {
        document.getElementById('scheduleLoading').style.display = 'none';
        document.getElementById('scheduleContainer').innerHTML = '<p class="result-error">Error loading scheduled messages: ' + error.message + '</p>';
        document.getElementById('scheduleList').style.display = 'block';
    });
}

function displayScheduledMessages(messages) {
    const container = document.getElementById('scheduleContainer');
    container.innerHTML = '';
    
    // Sort messages by scheduled time (closest first)
    messages.sort((a, b) => a.scheduled_timestamp - b.scheduled_timestamp);
    
    messages.forEach(message => {
        const messageDiv = document.createElement('div');
        messageDiv.className = 'schedule-item';
        
        // Convert unix timestamp to local time (24-hour format)
        const scheduledDate = new Date(message.scheduled_timestamp * 1000);
        const dateString = scheduledDate.toLocaleDateString('en-GB', {
            day: '2-digit',
            month: '2-digit',
            year: 'numeric'
        });
        const timeString = scheduledDate.toLocaleTimeString('en-GB', {
            hour: '2-digit',
            minute: '2-digit',
            hour12: false
        });
        
        // Calculate time remaining
        const now = new Date();
        const timeDiff = message.scheduled_timestamp * 1000 - now.getTime();
        let timeRemaining = '';
        
        if (timeDiff > 0) {
            const days = Math.floor(timeDiff / (1000 * 60 * 60 * 24));
            const hours = Math.floor((timeDiff % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
            const minutes = Math.floor((timeDiff % (1000 * 60 * 60)) / (1000 * 60));
            
            if (days > 0) {
                timeRemaining = `${days}d ${hours}h ${minutes}m`;
            } else if (hours > 0) {
                timeRemaining = `${hours}h ${minutes}m`;
            } else {
                timeRemaining = `${minutes}m`;
            }
        } else {
            timeRemaining = 'Overdue';
        }
        
        // Icon for deadman switch vs ordinary broadcast
        const iconType = message.dead_mans_switch ? 'deadman' : 'broadcast';
        const iconSvg = iconType === 'deadman' ? 
            '<path d="M480 208C480 128.5 408.4 64 320 64C231.6 64 160 128.5 160 208C160 255.1 185.1 296.9 224 323.2L224 352C224 369.7 238.3 384 256 384L384 384C401.7 384 416 369.7 416 352L416 323.2C454.9 296.9 480 255.1 480 208zM256 192C273.7 192 288 206.3 288 224C288 241.7 273.7 256 256 256C238.3 256 224 241.7 224 224C224 206.3 238.3 192 256 192zM352 224C352 206.3 366.3 192 384 192C401.7 192 416 206.3 416 224C416 241.7 401.7 256 384 256C366.3 256 352 241.7 352 224zM541.5 403.7C534.7 387.4 516 379.7 499.7 386.5L320 461.3L140.3 386.5C124 379.7 105.3 387.4 98.5 403.7C91.7 420 99.4 438.7 115.7 445.5L236.8 496L115.7 546.5C99.4 553.3 91.7 572 98.5 588.3C105.3 604.6 124 612.3 140.3 605.5L320 530.7L499.7 605.5C516 612.3 534.7 604.6 541.5 588.3C548.3 572 540.6 553.3 524.3 546.5L403.2 496L524.3 445.5C540.6 438.7 548.3 420 541.5 403.7z"/>' : 
            '<path d="M64 416L64 192C64 139 107 96 160 96L480 96C533 96 576 139 576 192L576 416C576 469 533 512 480 512L360 512C354.8 512 349.8 513.7 345.6 516.8L230.4 603.2C226.2 606.3 221.2 608 216 608C202.7 608 192 597.3 192 584L192 512L160 512C107 512 64 469 64 416z"/>';
        
        const isTouch = isMobileDevice();
        const iconInteraction = isTouch ? `onclick="showMessageContent('${message.id}', '${message.content.replace(/'/g, "\\'").replace(/"/g, '\\"')}', event)"` : `title="${message.content}"`;
        
        messageDiv.innerHTML = `
            <div class="schedule-row" onclick="toggleMessageSelection('${message.id}')" data-message-id="${message.id}">
                <div class="schedule-cell schedule-icon-cell">
                    <div class="schedule-icon ${iconType}" ${iconInteraction}>
                        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 640 640">
                            ${iconSvg}
                        </svg>
                    </div>
                </div>
                <div class="schedule-cell schedule-date-cell">${dateString}</div>
                <div class="schedule-cell schedule-time-cell">${timeString}</div>
                <div class="schedule-cell schedule-remaining-cell">${timeRemaining}</div>
                <div class="schedule-cell schedule-title-cell">${message.title}</div>
            </div>
        `;
        
        container.appendChild(messageDiv);
    });
}

let selectedMessages = new Set();

function toggleMessageSelection(messageId) {
    const messageItem = document.querySelector(`[data-message-id="${messageId}"]`).parentElement;
    
    if (selectedMessages.has(messageId)) {
        selectedMessages.delete(messageId);
        messageItem.classList.remove('selected');
    } else {
        selectedMessages.add(messageId);
        messageItem.classList.add('selected');
    }
    
    updateDeleteButton();
}

function updateDeleteButton() {
    const deleteBtn = document.getElementById('deleteSelectedBtn');
    const hasSelection = selectedMessages.size > 0;
    
    if (hasSelection) {
        deleteBtn.classList.remove('disabled');
        deleteBtn.disabled = false;
    } else {
        deleteBtn.classList.add('disabled');
        deleteBtn.disabled = true;
    }
}

function showMessageContent(messageId, content, event) {
    event.stopPropagation(); // Prevent triggering row selection
    
    // Create a simple alert for mobile devices
    alert(content);
}

function deleteSelectedMessages() {
    const selectedIds = Array.from(selectedMessages);
    
    if (selectedIds.length === 0) {
        return;
    }
    
    const confirmText = selectedIds.length === 1 ? 
        'Delete this scheduled message?' : 
        `Delete ${selectedIds.length} scheduled messages?`;
    
    if (confirm(confirmText)) {
        fetch('/delete-scheduled-messages', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message_ids: selectedIds })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                selectedMessages.clear(); // Clear selection
                loadScheduledMessages(); // Reload the list
                updateDeleteButton(); // Update button state
            } else {
                alert('Error deleting messages: ' + data.error);
            }
        })
        .catch(error => {
            alert('Network error: ' + error.message);
        });
    }
}

function toggleScheduleOptions() {
    const sendNow = document.querySelector('input[name="send_timing"][value="now"]').checked;
    const scheduleOptions = document.getElementById('scheduleOptions');
    scheduleOptions.style.display = sendNow ? 'none' : 'block';
}

function toggleScheduleInputs() {
    const specificTime = document.querySelector('input[name="schedule_type"][value="specific"]').checked;
    const relativeTime = document.querySelector('input[name="schedule_type"][value="relative"]').checked;
    const deadMansSwitch = document.querySelector('input[name="schedule_type"][value="dead_mans_switch"]').checked;
    
    const specificInputs = document.getElementById('specificTimeInputs');
    const relativeInputs = document.getElementById('relativeTimeInputs');
    const deadMansSwitchInputs = document.getElementById('deadMansSwitchInputs');
    const resetWordInput = document.getElementById('reset_word');
    
    specificInputs.style.display = specificTime ? 'block' : 'none';
    relativeInputs.style.display = relativeTime ? 'block' : 'none';
    deadMansSwitchInputs.style.display = deadMansSwitch ? 'block' : 'none';
    
    // Only make reset_word required when dead man's switch is selected
    if (resetWordInput) {
        resetWordInput.required = deadMansSwitch;
    }
}

// Contact Management
function loadContacts() {
    fetch('/get-contacts')
    .then(response => response.json())
    .then(data => {
        document.getElementById('contactsLoading').style.display = 'none';
        
        if (data.success && data.contacts.length > 0) {
            displayContacts(data.contacts);
            document.getElementById('contactsList').style.display = 'block';
        } else {
            document.getElementById('contactsContainer').innerHTML = '<p>No contacts found.</p>';
            document.getElementById('contactsList').style.display = 'block';
        }
    })
    .catch(error => {
        document.getElementById('contactsLoading').style.display = 'none';
        document.getElementById('contactsContainer').innerHTML = '<p class="result-error">Error loading contacts: ' + error.message + '</p>';
        document.getElementById('contactsList').style.display = 'block';
    });
}

function displayContacts(contacts) {
    const container = document.getElementById('contactsContainer');
    container.innerHTML = '';
    
    contacts.forEach(contact => {
        const contactDiv = document.createElement('div');
        contactDiv.className = 'contact-item';
        const statusClass = contact.connected ? 'status-online' : 'status-offline';
        const statusText = contact.connected ? 'Online' : 'Offline';
        
        contactDiv.innerHTML = `
            <div class="contact-info">
                <span class="contact-name">${contact.alias}</span>
                <div class="contact-right">
                    <span class="contact-status ${statusClass}">${statusText}</span>
                    <button class="delete-contact-btn" onclick="deleteContact(${contact.contactId}, '${contact.alias}')" title="Delete Contact">×</button>
                </div>
            </div>
        `;
        container.appendChild(contactDiv);
    });
}


// Form Handlers
document.getElementById('addContactForm').addEventListener('submit', function(e) {
    e.preventDefault();
    
    const formData = new FormData(this);
    const submitButton = this.querySelector('button[type="submit"]');
    const resultDiv = document.getElementById('addContactResult');
    
    submitButton.disabled = true;
    submitButton.textContent = 'Adding...';
    
    fetch('/add-contact', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showToastFeedback('Contact added successfully! Pending ID: ' + data.data.pendingContactId);
            hideAddContactModal();
            location.reload();
        } else {
            showToastFeedback('Error: ' + data.error, true);
        }
    })
    .catch(error => {
        showToastFeedback('Network error: ' + error.message, true);
    })
    .finally(() => {
        submitButton.disabled = false;
        submitButton.textContent = 'Add Contact';
    });
});

document.getElementById('broadcastForm').addEventListener('submit', function(e) {
    e.preventDefault();
    
    const formData = new FormData(this);
    const submitButton = this.querySelector('button[type="submit"]');
    const resultDiv = document.getElementById('broadcastResult');
    
    // Check if scheduling is requested
    const isScheduled = document.querySelector('input[name="send_timing"][value="scheduled"]').checked;
    
    if (isScheduled) {
        const isSpecificTime = document.querySelector('input[name="schedule_type"][value="specific"]').checked;
        const isRelativeTime = document.querySelector('input[name="schedule_type"][value="relative"]').checked;
        const isDeadMansSwitch = document.querySelector('input[name="schedule_type"][value="dead_mans_switch"]').checked;
        
        if (isSpecificTime) {
            // Handle specific date/time scheduling
            const scheduleDate = document.getElementById('schedule_date').value;
            const scheduleHour = document.getElementById('schedule_hour').value;
            const scheduleMinute = document.getElementById('schedule_minute').value;
            
            if (scheduleDate && scheduleHour && scheduleMinute) {
                const hourPadded = scheduleHour.padStart(2, '0');
                const minutePadded = scheduleMinute.padStart(2, '0');
                const scheduleTime = hourPadded + ':' + minutePadded;
                formData.append('schedule_date', scheduleDate);
                formData.append('schedule_time', scheduleTime);
            } else {
                showToastFeedback('Please enter a valid date and time for scheduling.', true);
                return;
            }
        } else if (isRelativeTime) {
            // Handle relative time scheduling
            const relativeAmount = document.getElementById('relative_amount').value;
            const relativeUnit = document.getElementById('relative_unit').value;
            
            if (relativeAmount && parseInt(relativeAmount) > 0) {
                // Remove the empty form field values first to prevent conflicts
                formData.delete('schedule_date');
                formData.delete('schedule_time');
                
                // Calculate future timestamp
                const now = new Date();
                let futureTime = new Date(now);
                
                const amount = parseInt(relativeAmount);
                
                switch (relativeUnit) {
                    case 'minutes':
                        futureTime.setMinutes(futureTime.getMinutes() + amount);
                        break;
                    case 'hours':
                        futureTime.setHours(futureTime.getHours() + amount);
                        break;
                    case 'days':
                        futureTime.setDate(futureTime.getDate() + amount);
                        break;
                    case 'weeks':
                        futureTime.setDate(futureTime.getDate() + (amount * 7));
                        break;
                    case 'months':
                        futureTime.setMonth(futureTime.getMonth() + amount);
                        break;
                    case 'years':
                        futureTime.setFullYear(futureTime.getFullYear() + amount);
                        break;
                }
                
                
                // Convert to date and time format for backend (local time)
                const year = futureTime.getFullYear();
                const month = String(futureTime.getMonth() + 1).padStart(2, '0');
                const day = String(futureTime.getDate()).padStart(2, '0');
                const hours = String(futureTime.getHours()).padStart(2, '0');
                const minutes = String(futureTime.getMinutes()).padStart(2, '0');
                
                const scheduleDate = `${year}-${month}-${day}`;
                const scheduleTime = `${hours}:${minutes}`;
                
                
                formData.append('schedule_date', scheduleDate);
                formData.append('schedule_time', scheduleTime);
                
            } else {
                showToastFeedback('Please enter a valid relative time amount.', true);
                return;
            }
        } else if (isDeadMansSwitch) {
            // Handle dead man's switch
            const dmsAmount = document.getElementById('dms_amount').value;
            const dmsUnit = document.getElementById('dms_unit').value;
            const resetWord = document.getElementById('reset_word').value;
            
            if (dmsAmount && parseInt(dmsAmount) > 0 && resetWord.trim()) {
                // Remove conflicting form fields
                formData.delete('schedule_date');
                formData.delete('schedule_time');
                
                // Add dead man's switch specific data
                formData.append('dead_mans_switch', 'true');
                formData.append('dms_amount', dmsAmount);
                formData.append('dms_unit', dmsUnit);
                formData.append('reset_word', resetWord.trim());
            } else {
                showToastFeedback('Please enter valid dead man\'s switch interval and reset word.', true);
                return;
            }
        }
    }
    
    submitButton.disabled = true;
    submitButton.textContent = isScheduled ? 'Scheduling...' : 'Sending...';
    
    fetch('/broadcast-message', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            if (data.scheduled) {
                showToastFeedback('Message scheduled successfully for ' + data.scheduled_time);
            } else {
                showToastFeedback('Broadcast sent successfully! Delivered to ' + data.successful + ' of ' + data.total_contacts + ' contacts.');
            }
            hideBroadcastModal();
        } else {
            showToastFeedback('Error: ' + data.error, true);
        }
    })
    .catch(error => {
        showToastFeedback('Network error: ' + error.message, true);
    })
    .finally(() => {
        submitButton.disabled = false;
        submitButton.textContent = 'Send Broadcast';
    });
});

function deleteContact(contactId, contactName) {
    if (confirm(`Delete contact "${contactName}"?`)) {
        fetch('/remove-contacts', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({contact_ids: [contactId]})
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                loadContacts(); // Reload the contact list
            } else {
                alert('Error deleting contact: ' + data.error);
            }
        })
        .catch(error => {
            alert('Network error: ' + error.message);
        });
    }
}

// Modal click-outside handling
window.onclick = function(event) {
    const modals = ['addContactModal', 'listContactsModal', 'broadcastModal', 'qrModal', 'deleteIdentityModal', 'scheduleModal'];
    modals.forEach(modalId => {
        const modal = document.getElementById(modalId);
        if (event.target === modal) {
            modal.style.display = 'none';
        }
    });
}

function showDeleteIdentityModal() {
    document.getElementById('deleteIdentityModal').style.display = 'block';
    document.getElementById('deleteConfirmation').value = '';
    document.getElementById('deleteIdentityBtn').disabled = true;
}

function hideDeleteIdentityModal() {
    document.getElementById('deleteIdentityModal').style.display = 'none';
}

function validateDeleteConfirmation() {
    const input = document.getElementById('deleteConfirmation');
    const button = document.getElementById('deleteIdentityBtn');
    const isValid = input.value.toLowerCase() === 'delete';
    button.disabled = !isValid;
    return isValid;
}

// Initialize
document.addEventListener('DOMContentLoaded', function() {
    // Add delete confirmation validation
    const deleteInput = document.getElementById('deleteConfirmation');
    if (deleteInput) {
        deleteInput.addEventListener('input', validateDeleteConfirmation);
    }
    
    // Add delete form handler
    const deleteForm = document.getElementById('deleteIdentityForm');
    if (deleteForm) {
        deleteForm.addEventListener('submit', function(e) {
            e.preventDefault();
            if (validateDeleteConfirmation()) {
                window.location.href = '/delete-identity';
            }
        });
    }
});