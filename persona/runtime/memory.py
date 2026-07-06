"""Conversation memory — in-process message history."""

from __future__ import annotations

from persona.core.response import Message


class ConversationMemory:
    """In-process conversation memory with configurable window size.

    Stores message history per session. Messages are lost on process restart.
    """

    def __init__(self, max_messages: int = 50):
        self._sessions: dict[str, list[Message]] = {}
        self._max_messages = max_messages

    def get_messages(self, session_id: str) -> list[Message]:
        """Get conversation history for a session."""
        return list(self._sessions.get(session_id, []))

    def add_message(self, session_id: str, message: Message) -> None:
        """Add a message to session history."""
        if session_id not in self._sessions:
            self._sessions[session_id] = []

        self._sessions[session_id].append(message)

        # Trim to max (keep system messages + recent)
        messages = self._sessions[session_id]
        if len(messages) > self._max_messages:
            # Keep first message (usually system context) + last N
            self._sessions[session_id] = messages[:1] + messages[-(self._max_messages - 1):]

    def clear_session(self, session_id: str) -> None:
        """Clear history for a session."""
        self._sessions.pop(session_id, None)

    def list_sessions(self) -> list[str]:
        """List all active session IDs."""
        return list(self._sessions.keys())
