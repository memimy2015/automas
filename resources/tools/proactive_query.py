from control.notifier import Notifier
from control.context_manager import ContextManager

context_manager = ContextManager()
notifier = Notifier(context_manager)

def call_user(query: str) -> str:
    """
    Call user to get more information.
    """
    return notifier.call_user(query)
