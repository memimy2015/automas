from typing import List
from resources.tools.console_input import get_input
from control.context_manager import ContextManager
import os
from datetime import datetime

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
    def call_user(self, notification_msg: str, invoker_agent_id: int, in_channel: str, out_channel: str | List[str] = "user"):
        """
        Call the user to get more informations.
        Args:
            notification_msg (str): The notification message to print.
            invoker_agent_id (int): The ID of the agent that invokes this notifier.
            in_channel (str): The channel to send the user output. **Not in use currently**.
            out_channel (str, optional): The channel to receive the user input. Defaults to "user".
        Returns:
            str: The user input.
        """
        if in_channel == self.context_manager.consistentAgent2DefaultChannel["Planner"]:
            notification_msg = "Planner: " + notification_msg
        elif in_channel == self.context_manager.consistentAgent2DefaultChannel["Summarizer"]:
            notification_msg = "Summarizer: " + notification_msg
        elif in_channel == self.context_manager.consistentAgent2DefaultChannel["Claimer"]:
            notification_msg = "Claimer: " + notification_msg
        else:
            notification_msg = "Agent " + str(invoker_agent_id) + ": " + notification_msg
        print("Current Objective needs more informations")
        self.context_manager.add_dialogue(invoker_agent_id, out_channel, [{"role": "assistant", "content": notification_msg} | {"timestamp": datetime.now().timestamp()}])
        msg = get_input("====Notification====\n" + notification_msg + "\n")
        self.context_manager.add_dialogue(invoker_agent_id, out_channel, [{"role": "user", "content": msg} | {"timestamp": datetime.now().timestamp()}])   
        print("====Notification END====")
        return msg
        
    