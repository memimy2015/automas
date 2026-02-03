import os

class Notifier:
    def __init__(self):
        pass
    
    # for test
    def call_user(self, notification_msg: str):
        print("Current Objective needs more infomations")
        msg = input("====Notification====\n" + notification_msg + "\n")
        print(f"User added: {msg}")
        print("====Notification END====")
        return msg
        
    
if __name__ == "__main__":
    notifier = Notifier()
    msg = notifier.call_user("Need file for xxx")
    print(msg)
    