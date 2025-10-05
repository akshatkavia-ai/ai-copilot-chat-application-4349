from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List


@dataclass
class SessionNotFoundError(Exception):
    """Raised when a session cannot be found in the store."""

    session_id: str

    def __str__(self) -> str:
        return f"Session '{self.session_id}' not found"


class InMemorySessionStore:
    """A simple in-memory, thread-safe session and history store.

    This implementation is intended for development and testing only.
    It keeps all data in memory and is not persistent.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        # Maps session_id -> {'id': str, 'title': str, 'created_at': datetime}
        self._sessions: Dict[str, Dict[str, Any]] = {}
        # Maps session_id -> List[{'id': str, 'role': str, 'content': str, 'timestamp': datetime}]
        self._history: Dict[str, List[Dict[str, Any]]] = {}

    # PUBLIC_INTERFACE
    def has_session(self, session_id: str) -> bool:
        """Return True if a session exists, False otherwise."""
        with self._lock:
            return session_id in self._sessions

    # PUBLIC_INTERFACE
    def create_session(self, title: str | None = None) -> Dict[str, Any]:
        """Create a new session and return its metadata dictionary.

        The returned dict has keys: id, title, created_at.
        """
        session_id = str(uuid.uuid4())
        created_at = datetime.now(timezone.utc)
        session = {
            "id": session_id,
            "title": title or "New Chat",
            "created_at": created_at,
        }
        with self._lock:
            self._sessions[session_id] = session
            self._history[session_id] = []
        return session

    # PUBLIC_INTERFACE
    def list_sessions(self) -> List[Dict[str, Any]]:
        """Return a list of session metadata dictionaries."""
        with self._lock:
            # Return shallow copies to prevent accidental mutation
            return [dict(s) for s in self._sessions.values()]

    # PUBLIC_INTERFACE
    def append_message(self, session_id: str, role: str, content: str) -> Dict[str, Any]:
        """Append a message to the specified session and return the message dict.

        Raises:
            SessionNotFoundError: If the session does not exist.
        """
        message = {
            "id": str(uuid.uuid4()),
            "role": role,
            "content": content,
            "timestamp": datetime.now(timezone.utc),
        }
        with self._lock:
            if session_id not in self._sessions:
                raise SessionNotFoundError(session_id)
            self._history[session_id].append(message)
        return message

    # PUBLIC_INTERFACE
    def get_history(self, session_id: str) -> List[Dict[str, Any]]:
        """Return the message history for a session.

        Raises:
            SessionNotFoundError: If the session does not exist.
        """
        with self._lock:
            if session_id not in self._sessions:
                raise SessionNotFoundError(session_id)
            return [dict(m) for m in self._history[session_id]]
