from miscellaneous.cozeloop_preprocess import summarizer_process_output
from typing import List
from control.context_manager import ContextManager
from resources.tools.persistent_shell import PersistentShell
from resources.tools.skill_tool import get_skill_list
import json
from resources.tools.tool_executer import ToolExecuter
from llm.llm import llm_call, llm_call_json_schema
from llm.json_schemas import ProactiveQuery, ClaimerSchema
from execution.agent.prompt import render
from .notifier import Notifier
from datetime import datetime
from miscellaneous.observe import observe

def access_knowledgeDB():
    return "None"

DEFAULT_INSTRUCTION = """
# Role Definition
You are a **File Extraction and Information Summarization Specialist** serving the user request response system.
Your core responsibility is to accurately identify and extract all files required for the user to accomplish their objective from the provided context, and to provide structured summaries of relevant historical information.
Your work must be precise, complete, and strictly aligned with the user’s stated goal and the planner’s task requirements.

# Operational Guidelines

## Mandatory Requirements

1. If the user’s objective explicitly specifies a file type, you must prioritize extracting files of that type.
2. If the planner’s task specifies reference files, those files must be included in the extraction scope.
3. All files produced by subagents must be reviewed; any file relevant to the user’s objective must be extracted.
4. Ensure accuracy and completeness — no incorrect information, omissions, or misinterpretations are allowed.

## Prohibited Actions

1. Do not extract files unrelated to the user’s objective or the planner’s task.
2. Do not omit any file explicitly associated with the user’s objective in the context.
3. Do not modify file contents or rename files; preserve original file names exactly as provided.

# Output Requirements

1. Structure the output as follows:

   * First, list **Core Resources** (essential to fulfilling the user’s objective).
   * Then, list **Supporting Resources** (auxiliary but relevant materials).

2. The output must be formatted in **Markdown**, and for each resource include:

   * Resource Name
   * Resource URI
   * A concise description of its purpose and relevance
"""

class SummarizerAgent:
    def __init__(self, notifier: Notifier, context_manager: ContextManager):
        self.messages = []
        prompt = DEFAULT_INSTRUCTION
        self.notifier = notifier
        self.context_manager = context_manager
        # 注册 Agent id 和 channel
        # self.context_manager.add_active_subagent(self.agent_id, self.identity + "_main")
        # self.context_manager.register_consistent_subagent(self.agent_id, self.identity + "_main", "Summarizer")
        agent_id, channel = self.context_manager.get_consistent_agent_identity("Summarizer")
        if agent_id is not None and channel:
            self.agent_id = agent_id
            self.identity = channel.rsplit("_main", 1)[0]
            if channel not in self.context_manager.dialogue_history:
                self.context_manager.add_active_subagent(self.agent_id, channel, dump=False)
        else:
            self.agent_id = self.context_manager.obtain_id(dump=False)
            self.identity = f"SummarizerAgent_{self.agent_id}"
            self.context_manager.register_consistent_subagent(self.agent_id, self.identity + "_main", "Summarizer", dump=False)
            self.append_message({"role": "system", "content": prompt}, self.identity + "_main", dump=False)

    def append_message(self, message: dict, channel: str | List[str] = None, usage: dict = None, dump: bool = True):
        """
        Append a message to the message list of the channel and current agent message list.
        Args:
            message (dict): The message to append.
            channel (str, optional): The channel to append the message to. Defaults to None.
        """
        if channel is None:
            channel = self.identity + "_main"
        # self.messages.append(message) # 不能删，Summarizer只执行一次，所以没有prepare_context函数为每次执行提供上下文吗，这里选择直接加入messages
        self.context_manager.add_dialogue(self.agent_id, channel, [message | {"timestamp": datetime.now().timestamp()} | {"usage": usage}], dump=dump) # 只用作记录
    
    # def extend_messages(self, messages: list):
    #     self.messages.extend(messages)
    
    @observe(
        name="summarizer",
        span_type="summarizer_span",
        process_outputs=summarizer_process_output,
    )
    def run(self):
        try:
            task_status = self.context_manager.get_task_status()[0]
            formatted_status = self.context_manager.get_formatted_plan(task_status)
            self.append_message(
                {
                    "role": "user", 
                    "content": f"当前任务已结束，描述信息为：\n {formatted_status}"
                }   
                ,
                self.identity + "_main",
                dump=False
            )
            self.append_message(
                {
                    "role": "user",
                    "content": f"根据之前的信息，找出我一开始提出的要求所对应的资源，需要名字、描述和URI，确保信息准确，并且详细的总结一下信息。我一开始的要求是：{self.context_manager.overall_goal}"
                },
                self.identity + "_main",
                dump=True
            )
            self._prepare_context()
            finish_reason, resp, usage = llm_call(messages=self.messages, tools=[])
            if finish_reason == "error":
                raise RuntimeError(resp.content)
            self.append_message(
                {
                    "role": "assistant",
                    "content": resp.model_dump()
                },
                self.identity + "_main",
                dump=True
            )
            return resp.content, usage
        finally:
            self.context_manager._auto_dump("summarizer_exit", {"agent_id": self.agent_id})
    
    def _prepare_context(self):
        self.messages = self.context_manager.get_dialogue(invoker_channel=self.identity + "_main", filter=["*_summary", "user", "Claimer*", self.identity + "_main"], formatted=False)
        
        
