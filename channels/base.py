from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class InboundMessage:
    chat_id: str
    message_id: str
    text: str
    user_id: Optional[str] = None

