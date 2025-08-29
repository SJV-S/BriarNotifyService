
import json, threading, websocket
from internal_service.service_config import auth_manager, WS_URL
from internal_service.dead_mans_switch import get_dead_mans_switch

class BriarEventListener:
    def __init__(self, url: str = WS_URL):
        self.url = url
        self._thread = None

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    # --- internals ---

    def _run(self):
        def on_open(ws):
            try:
                token = auth_manager.get_token()
                if token:
                    ws.send(token)  # send token first
                else:
                    ws.close()
            except Exception:
                ws.close()

        def on_event(ws, raw):
            try:
                evt = json.loads(raw)
            except Exception:
                return

            name = evt.get("name")
            data = evt.get("data") or {}

            event_handlers = {
                "ContactConnectedEvent": lambda: self.on_contact_connected(data.get("contactId")),
                "ContactDisconnectedEvent": lambda: self.on_contact_disconnected(data.get("contactId")),
                "ConversationMessageReceivedEvent": lambda: self._handle_conversation_message(data),
                "MessagesSentEvent": lambda: self.on_messages_sent(data.get("contactId"), data.get("messageIds", [])),
                "MessagesAckedEvent": lambda: self.on_messages_acked(data.get("contactId"), data.get("messageIds", [])),
            }

            handler = event_handlers.get(name)
            if handler:
                handler()
            else:
                self.on_other_event(name, data)

        websocket.WebSocketApp(
            self.url, on_open=on_open, on_message=on_event
        ).run_forever(ping_interval=30, ping_timeout=10)

    def _handle_conversation_message(self, data):
        # All 1:1 text messages (both incoming and outgoing)
        if data.get("type") == "PrivateMessage":
            self.message_traffic(
                contact_id=data.get("contactId"),
                text=data.get("text"),
                full=data,
            )
        else:
            self.on_conversation_event(data)

    # --- handlers: replace prints with your app logic ---

    def on_contact_connected(self, contact_id):
        pass

    def on_contact_disconnected(self, contact_id):
        pass

    def message_traffic(self, contact_id, text, full):
        if full.get("local", False):
            # Outgoing
            pass
        else:
            # Incoming

            # Process message through dead man's switch
            try:
                dms = get_dead_mans_switch()
                dms.process_incoming_message(contact_id, text, full)
            except Exception as e:
                print(f"[ERROR] Dead man's switch processing failed: {e}")

    def on_conversation_event(self, data):
        # handle non-text or group events if needed
        pass

    def on_messages_sent(self, contact_id, message_ids):
        # Update outbox state / UI (sent)
        pass

    def on_messages_acked(self, contact_id, message_ids):
        # mark messages as acknowledged
        pass

    def on_other_event(self, name, data):
        pass


# Keep the same public entrypoint your app already calls
_listener = BriarEventListener()

def start_event_listener():
    if getattr(start_event_listener, "_started", False):
        return
    start_event_listener._started = True
    _listener.start()
