import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List, Dict, Any

import aiosqlite
from app.config import get_settings
from app.schemas.chat import KnowledgeCitation

logger = logging.getLogger("chatbot.session_service")

class SessionService:
    """
    Manages conversational session persistence, multi-turn history,
    user feedback, and escalation tracking using local SQLite (aiosqlite).
    """

    def __init__(self, db_path: Optional[str] = None):
        self.settings = get_settings()
        self.db_path = db_path or self.settings.DATABASE_PATH
        self._initialized = False

    async def init_db(self):
        """Initializes database tables with proper indexing."""
        if self._initialized:
            return

        db_file = Path(self.db_path)
        db_file.parent.mkdir(parents=True, exist_ok=True)

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    brand TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    citations_json TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (session_id) REFERENCES sessions (session_id)
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS feedback (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    message_id TEXT NOT NULL,
                    rating TEXT NOT NULL,
                    comment TEXT,
                    created_at TEXT NOT NULL
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS escalations (
                    ticket_id TEXT PRIMARY KEY,
                    session_id TEXT,
                    brand TEXT NOT NULL,
                    query TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    urgency TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
            """)
            await db.execute("CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_feedback_session ON feedback(session_id)")
            await db.commit()

        self._initialized = True
        logger.info(f"SQLite Session database initialized at: {self.db_path}")

    def _now_iso(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    async def get_or_create_session(self, session_id: Optional[str] = None, brand: Optional[str] = None) -> str:
        """Returns existing session or creates a new one with a distinct UUID."""
        await self.init_db()
        now = self._now_iso()

        if session_id:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute("SELECT session_id FROM sessions WHERE session_id = ?", (session_id,)) as cursor:
                    row = await cursor.fetchone()
                    if row:
                        await db.execute("UPDATE sessions SET updated_at = ? WHERE session_id = ?", (now, session_id))
                        await db.commit()
                        return session_id

        # Generate new session ID
        new_id = session_id or f"sess_{uuid.uuid4().hex[:12]}"
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT OR REPLACE INTO sessions (session_id, brand, created_at, updated_at) VALUES (?, ?, ?, ?)",
                (new_id, brand, now, now)
            )
            await db.commit()
        return new_id

    async def save_message(
        self,
        session_id: str,
        role: str,
        content: str,
        citations: Optional[List[KnowledgeCitation]] = None,
        message_id: Optional[str] = None
    ) -> str:
        """Persists a user or assistant message to the session thread."""
        await self.init_db()
        msg_id = message_id or f"{role}_{uuid.uuid4().hex[:10]}"
        now = self._now_iso()
        citations_json = json.dumps([c.model_dump() for c in citations]) if citations else None

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT INTO messages (id, session_id, role, content, citations_json, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (msg_id, session_id, role, content, citations_json, now)
            )
            await db.execute("UPDATE sessions SET updated_at = ? WHERE session_id = ?", (now, session_id))
            await db.commit()

        return msg_id

    async def get_session_history(self, session_id: str) -> Dict[str, Any]:
        """Fetches all chronological messages and metadata for a session."""
        await self.init_db()
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM sessions WHERE session_id = ?", (session_id,)) as cur:
                sess_row = await cur.fetchone()
                if not sess_row:
                    return {"session_id": session_id, "brand": None, "created_at": self._now_iso(), "messages": []}

            async with db.execute("SELECT * FROM messages WHERE session_id = ? ORDER BY created_at ASC", (session_id,)) as cur:
                msg_rows = await cur.fetchall()

            messages = []
            for row in msg_rows:
                cit_data = []
                if row["citations_json"]:
                    try:
                        cit_data = json.loads(row["citations_json"])
                    except Exception:
                        pass
                messages.append({
                    "id": row["id"],
                    "role": row["role"],
                    "content": row["content"],
                    "citations": cit_data,
                    "created_at": row["created_at"]
                })

            return {
                "session_id": sess_row["session_id"],
                "brand": sess_row["brand"],
                "created_at": sess_row["created_at"],
                "messages": messages
            }

    async def save_feedback(
        self,
        session_id: str,
        message_id: str,
        rating: str,
        comment: Optional[str] = None
    ) -> bool:
        """Stores user sentiment feedback for offline dataset synthesis and quality monitoring."""
        await self.init_db()
        now = self._now_iso()
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT INTO feedback (session_id, message_id, rating, comment, created_at) VALUES (?, ?, ?, ?, ?)",
                (session_id, message_id, rating, comment, now)
            )
            await db.commit()
        logger.info(f"Recorded {rating} feedback for message {message_id} in session {session_id}")
        return True

    async def save_escalation(
        self,
        ticket_id: str,
        session_id: Optional[str],
        brand: str,
        query: str,
        reason: str,
        urgency: str = "high"
    ) -> bool:
        """Logs a customer support escalation event."""
        await self.init_db()
        now = self._now_iso()
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT OR REPLACE INTO escalations (ticket_id, session_id, brand, query, reason, urgency, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (ticket_id, session_id, brand, query, reason, urgency, now)
            )
            await db.commit()
        logger.info(f"Escalation logged: ticket {ticket_id} for brand {brand}")
        return True

    async def get_escalations(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Retrieves recent escalation tickets for the admin dashboard."""
        await self.init_db()
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM escalations ORDER BY created_at DESC LIMIT ?", (limit,)) as cur:
                rows = await cur.fetchall()
                return [dict(row) for row in rows]

    async def get_feedback(self, negative_only: bool = False, limit: int = 50) -> List[Dict[str, Any]]:
        """Retrieves recent user feedback ratings for admin evaluation."""
        await self.init_db()
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            if negative_only:
                query = "SELECT * FROM feedback WHERE rating = 'down' ORDER BY created_at DESC LIMIT ?"
            else:
                query = "SELECT * FROM feedback ORDER BY created_at DESC LIMIT ?"
            async with db.execute(query, (limit,)) as cur:
                rows = await cur.fetchall()
                return [dict(row) for row in rows]

_session_service_instance: Optional[SessionService] = None

def get_session_service() -> SessionService:
    global _session_service_instance
    if _session_service_instance is None:
        _session_service_instance = SessionService()
    return _session_service_instance
