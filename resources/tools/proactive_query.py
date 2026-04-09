from control.notifier import Notifier
from control.context_manager import ContextManager
from typing import List

context_manager = ContextManager()
notifier = Notifier(context_manager)

def call_user(query: str, invoker_agent_id: int, in_channel: str, out_channel: str | List[str] = "user") -> str:
    """
    Call user to get more information.
    """
    return notifier.call_user(query, invoker_agent_id, in_channel, out_channel)
