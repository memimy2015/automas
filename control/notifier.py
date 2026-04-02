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
            notification_msg = "规划者: " + notification_msg
        elif in_channel == self.context_manager.consistentAgent2DefaultChannel["Summarizer"]:
            notification_msg = "总结者: " + notification_msg
        elif in_channel == self.context_manager.consistentAgent2DefaultChannel["Clarifier"]:
            notification_msg = "澄清者: " + notification_msg
        else:
            notification_msg = self.context_manager.latest_agent_factory_output.role_name + ": " + notification_msg
        print("Current Objective needs more informations")
        self.context_manager.add_dialogue(invoker_agent_id, out_channel, [{"role": "assistant", "content": notification_msg} | {"timestamp": datetime.now().timestamp()}])

        # 网页模式下注册问题到 InputBuffer
        if os.environ.get("AUTOMAS_WEB_MODE") == "1":
            task_id = os.environ.get("AUTOMAS_TASK_ID")
            if task_id:
                # 提取纯问题内容（去掉前缀）
                clean_query = notification_msg
                for prefix in ["澄清者: ", "规划者: ", "总结者: "]:
                    if clean_query.startswith(prefix):
                        clean_query = clean_query[len(prefix):]
                        break
                else:
                    # 检查是否是 "{role_name}: " 格式
                    if ": " in clean_query:
                        clean_query = clean_query.split(": ", 1)[1]
                
                # 使用 api.input_buffer 中的全局函数获取 InputBuffer 实例
                # 在子进程中，这会使用通过 set_queue 设置的全局队列
                from api.input_buffer import register_query
                register_query(task_id, clean_query)

        # 通知状态变更（用户收到提问）
        if hasattr(self.context_manager, '_notify_state_change'):
            self.context_manager._notify_state_change("call_user")

        msg = get_input("====Notification====\n" + notification_msg + "\n")
        self.context_manager.add_dialogue(invoker_agent_id, out_channel, [{"role": "user", "content": msg} | {"timestamp": datetime.now().timestamp()}])
        print("====Notification END====")
        if hasattr(self.context_manager, '_notify_state_change'):
            self.context_manager._notify_state_change("get_user_response")
        return msg
        
    