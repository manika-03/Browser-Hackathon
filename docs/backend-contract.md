# MORI Backend Contract

The gateway sends an HTTP `POST` to the exact `MORI_BACKEND_URL` for each text, command, or button event.

## Request

```json
{
  "schema_version": "1.0",
  "request_id": "uuid",
  "persona_id": "mori-v1",
  "channel": "telegram",
  "session_id": "telegram:123456",
  "occurred_at": "2026-08-08T13:00:00+00:00",
  "user": {
    "id": "123",
    "display_name": "Priya",
    "username": "username",
    "language_code": "en"
  },
  "conversation": {
    "chat_id": "123456",
    "chat_type": "private",
    "message_id": 42
  },
  "event": {
    "type": "text",
    "text": "I want to become an ML engineer."
  }
}
```

Event types are `text`, `action` with `action_id`, and `command` with `command`.

## Response

```json
{
  "text": "I can build that route. What should I optimize for?",
  "actions": [
    {"id": "goal:free", "label": "Mostly free", "kind": "callback"},
    {"id": "course:1", "label": "Open course", "kind": "url", "url": "https://example.com"}
  ]
}
```

Callback IDs must be no longer than 48 UTF-8 bytes. URL actions must use HTTPS. The backend must validate ownership, expiry, and the immutable pending payload for approvals. Requests are not automatically retried because an event may represent a sensitive action.

