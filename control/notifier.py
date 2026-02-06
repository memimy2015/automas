from control.context_manager import ContextManager
import os

class Notifier:
    def __init__(self, context_manager: ContextManager):
        self.context_manager = context_manager  
    
    # for test
    def call_user(self, notification_msg: str):
        print("Current Objective needs more infomations")
        msg = input("====Notification====\n" + notification_msg + "\n")
        self.context_manager.add_dialogue({"role": "assistant", "content": notification_msg})
        print(f"User added: {msg}")
        self.context_manager.add_dialogue({"role": "user", "content": msg})
        print("====Notification END====")
        return msg
        
    
if __name__ == "__main__":
    notifier = Notifier()
    msg = notifier.call_user("Need file for xxx")
    print(msg)
    