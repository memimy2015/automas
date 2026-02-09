from resources.tools.console_input import get_input
from control.context_manager import ContextManager
import os

class Notifier:
    _instance = None
    _initialized = False
    def __new__(cls, context_manager: ContextManager):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self, context_manager: ContextManager):
        if self._initialized:
            return
        self._initialized = True
        self.context_manager = context_manager
        print("=====Notifier initialized.=====")
    
    
    # for test
    def call_user(self, notification_msg: str):
        print("Current Objective needs more infomations")
        msg = get_input("====Notification====\n" + notification_msg + "\n")
        self.context_manager.add_dialogue({"role": "assistant", "content": notification_msg})
        self.context_manager.add_dialogue({"role": "user", "content": msg})
        print("====Notification END====")
        return msg
        
    
if __name__ == "__main__":
    notifier = Notifier()
    msg = notifier.call_user("Need file for xxx")
    print(msg)
    