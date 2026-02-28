from miscellaneous.cozeloop_preprocess import agent_process_output
from operator import sub
from datetime import datetime
from control.context_manager import ContextManager
from resources.tools.persistent_shell import PersistentShell
from resources.tools.skill_tool import get_skill_list
import json
from resources.tools.tool_executer import ToolExecuter
from llm.llm import llm_call, llm_call_json_schema
from .prompt import render
from typing import Dict, Any
from llm.json_schemas import SubmitMessage
from uuid import uuid4
import os
from miscellaneous.observe import observe

DEFAULT_SUBMIT_PROMPT = """
# Role 
You are an assistant specialized in reporting task execution results, serving task management scenarios. Your core responsibility is to extract key information from task execution data and generate structured reporting content.

# Core Rules
- **Mandatory Actions**: You must extract the following from task execution data:
  - The name of the currently executing task
  - Task summary
  - Task status (strictly limited to one of four values: "pending", "completed", "failed", or "cancelled")
  - A complete list of resources created during execution
- **Constraints**:
  - Task status must strictly match one of the four specified values; custom status values are prohibited
  - The resource list must comprehensively include all created resources without omission

# Output format
JSON format

Now, please generate the task execution results according to previous chat history.
"""

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
AUTOMAS_DIR = os.path.dirname(os.path.dirname(CURRENT_DIR))
Agent_LOG_DIR = os.path.join(AUTOMAS_DIR, "agent_log")

class Agent:
    def __init__(self, instruction: Dict[str, Any], tool_name_list: list, tool_executer: ToolExecuter, context_manager: ContextManager, shell: PersistentShell=None):
        os.makedirs(Agent_LOG_DIR, exist_ok=True)
        self.instruction = instruction
        self.tool_name_list = tool_name_list
        self.tool_executer = tool_executer 
        self.context_manager = context_manager
        self.shell = shell
        self.messages = []
        # 子代理id
        existing_agent_id = None
        is_existing_agent = False
        current_subtask_index, current_subtask_step_index = self.context_manager._get_current_indices()
        current_step = self.context_manager.get_subtask_step(current_subtask_index, current_subtask_step_index)
        if current_step.agent_id is not None:
            existing_agent_id = current_step.agent_id
        if existing_agent_id is not None:
            self.agent_id = existing_agent_id
            is_existing_agent = True
            if self.agent_id >= self.context_manager.next_agent_id:
                self.context_manager.next_agent_id = self.agent_id
        else:
            self.agent_id = self.context_manager.obtain_id()
        self.log_name = f"{datetime.now().strftime('%Y-%m-%d')}_{self.agent_id}.jsonl"
        prompt = render(**instruction)
        print(f"agent system prompt: {prompt}")
        self.message_logger(instruction)
        sub_objective_index, sub_objective_step_index = self.context_manager._get_current_indices()
        self.task_info = {
            "sub_objective_index": sub_objective_index,
            "sub_objective_step_index": sub_objective_step_index,
            "subtask_name": self.context_manager.get_subtask_step(sub_objective_index, sub_objective_step_index).sub_objective,
            "task_name": self.context_manager.get_subtask(sub_objective_index).task_name,
            "agent_id": self.agent_id
        }
        # 子代理身份标识
        self.identity = f"{self.task_info['subtask_name']}_subagent_{self.agent_id}"
        # 先注册一下 Agent id 以及默认信道
        self.context_manager.add_active_subagent(subagent_id=self.agent_id, default_channel=self.identity + "_main")
        # 设置子任务的agent_id
        self.context_manager.set_current_subtask_agent_id(self.agent_id)
        self.context_manager.set_latest_agent(self.agent_id)
        # 不存在的Agent可以记录一下系统提示词
        if not is_existing_agent:
            self.append_message({"role": "system", "content": prompt}, {}, channel=self.identity + "_main")


    def message_logger(self, message: dict):
        with open(os.path.join(Agent_LOG_DIR, self.log_name), "a") as f:
            f.write(json.dumps(message, ensure_ascii=False) + "\n")

    def append_message(self, message: dict, usage: dict, channel: str = None):
        """
        Append a message to the message list of the channel and current agent message list.
        Args:
            message (dict): The message to append.
            usage (dict): The usage of the message.
            channel (str, optional): The channel to append the message to. Defaults to None.
        """
        if channel is None:
            channel = self.identity + "_main"
        # self.messages.append(message)
        # 记录Agent消息日志
        if os.getenv("IS_DEBUG_ENABLED", "1") == "1":
            self.message_logger(message | self.task_info | {"time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")} | usage)
        # 记录Agent消息到上下文管理器
        self.context_manager.add_dialogue(self.agent_id, channel, [message | {"timestamp": datetime.now().timestamp()}])
        
    @observe(
        name="agent",
        span_type="agent_span",
        process_outputs=agent_process_output,
    )
    def run(self, query: str):
        self.context_manager.is_executing = True
        if query !=  "":
            self.append_message({"role": "user", "content": query}, {}, channel=self.identity + "_main")
        tools = []
        for tool_name in self.tool_name_list:
            tools.append(self.tool_executer.get_tool(tool_name))    
        while True:
            self._prepare_context()
            finish_reason, resp_msg, usage = llm_call(messages=self.messages, tools=tools)
            if finish_reason != "tool_calls":
                content = resp_msg.content
                self.append_message({"role": "assistant", "content": content}, usage.model_dump(), channel=self.identity + "_main")
                self.append_message({"role": "user", "content": DEFAULT_SUBMIT_PROMPT}, usage.model_dump(), channel=self.identity + "_main")
                try:
                    self._prepare_context()
                    finish_reason, resp_msg, submit_usage = llm_call_json_schema(messages=self.messages, tools=[], jsonSchema="Submit")
                    resp_msg = resp_msg.parsed
                    resources = {}
                    for resource in resp_msg.resource_reference:
                        resources[resource.description] = resource
                    print(f"submit {resp_msg.task_name}: \n {resp_msg.task_summary} \n status: {resp_msg.task_status}")
                    print(f"resources: {resources}")
                    
                    # 把执行反馈给自己的summary channel
                    current_subtask_index, current_subtask_step_index = self.context_manager._get_current_indices()
                    current_subtask_step = self.context_manager.get_subtask_step(current_subtask_index, current_subtask_step_index)
                    formatted_subtask_step = self.context_manager.get_formatted_subtask_step(current_subtask_step, current_subtask_index + 1, current_subtask_step_index + 1)   
                    self.append_message({"role": "user", "content": f"现在处理的子目标概况：\n {formatted_subtask_step} \n 执行概要为：{content}"}, usage.model_dump(), channel=self.identity + "_summary")
                    
                    self.context_manager.submit_sub_objective(resp_msg.task_summary, resp_msg.task_status, resources)
                    return content, usage, "success", self.tool_usage
                except Exception as e:
                    print(f"submit {self.messages[-1]} \n error: {e}")
                    error_summary = f"Error when submitting task execution results, error message: {e}"
                    self.context_manager.submit_sub_objective(error_summary, "pending", {})
                    return content, usage, str(e), self.tool_usage
            self.append_message(resp_msg.model_dump(), usage.model_dump(), channel=self.identity + "_main")
            tool_call = resp_msg.tool_calls[0]
            tool_name = tool_call.function.name
            tool_args = json.loads(tool_call.function.arguments)
            if tool_name == "call_user":
                tool_args["invoker_agent_id"] = self.agent_id
                tool_args["in_channel"] = self.identity + "_main"
                tool_args["out_channel"] = "user"
            self.context_manager.record_tool_usage(self.agent_id, tool_name)
            tool_result = self.tool_executer.call(tool_name, tool_args)
            self.append_message(
                {"role": "tool", "content": tool_result, "tool_call_id": tool_call.id, "tool_name": tool_name}, usage.model_dump(), channel=self.identity + "_main"
            )
    
    def _prepare_context(self):
        self.context_manager.handle_pending_tool_call(self.tool_executer, self.agent_id, self.identity + "_main")
        self.messages = self.context_manager.get_dialogue(invoker_channel=self.identity + "_main", filter=[self.identity + "_main"], formatted=False)
        if self.agent_id == self.context_manager.latest_agent_id:
            self.tool_usage = self.context_manager.latest_agent_tool_usage
