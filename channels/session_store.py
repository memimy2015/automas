import json
import os
import tempfile
import threading
from dataclasses import dataclass, asdict
from typing import Optional


@dataclass
class BotSession:
    active_task_id: Optional[str] = None
    active_chat_id: Optional[str] = None
    active_source_message_id: Optional[str] = None
    state_card_message_id: Optional[str] = None
    expecting_input: bool = False
    last_pending_query_sent: Optional[str] = None
    last_state_hash: Optional[str] = None


class SessionStore:
    def __init__(self, path: str):
        self._path = path
        self._lock = threading.Lock()

    def load(self) -> BotSession:
        with self._lock:
            if not os.path.exists(self._path):
                return BotSession()
            try:
                with open(self._path, "r", encoding="utf-8") as f:
                    raw = json.load(f)
                if not isinstance(raw, dict):
                    return BotSession()
                return BotSession(
                    active_task_id=raw.get("active_task_id"),
                    active_chat_id=raw.get("active_chat_id"),
                    active_source_message_id=raw.get("active_source_message_id"),
                    state_card_message_id=raw.get("state_card_message_id"),
                    expecting_input=bool(raw.get("expecting_input", False)),
                    last_pending_query_sent=raw.get("last_pending_query_sent"),
                    last_state_hash=raw.get("last_state_hash") or None,
                )
            except Exception:
                return BotSession()

    def save(self, session: BotSession) -> None:
        with self._lock:
            os.makedirs(os.path.dirname(self._path), exist_ok=True)
            data = asdict(session)
            fd, tmp_path = tempfile.mkstemp(prefix="._feishu_session_", dir=os.path.dirname(self._path))
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False)
                os.replace(tmp_path, self._path)
            finally:
                try:
                    if os.path.exists(tmp_path):
                        os.remove(tmp_path)
                except Exception:
                    pass
