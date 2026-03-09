from miscellaneous.cozeloop_preprocess import claimer_process_output
from typing import List
from datetime import datetime
from control.context_manager import ContextManager
from resources.tools.persistent_shell import PersistentShell
from resources.tools.skill_tool import get_skill_list
import json
from resources.tools.tool_executer import ToolExecuter
from llm.llm import llm_call, llm_call_json_schema
from llm.json_schemas import ProactiveQuery, ClaimerSchema
from execution.agent.prompt import render
from .notifier import Notifier
from miscellaneous.observe import observe
import os

def access_knowledgeDB():
    return "None"

DEFAULT_INSTRUCTION = """
# Role
You are an expert in user requirement assessment, skilled at evaluating whether the requirement currently proposed by the user is a complete and executable one.

# Target
The goal is to obtain an executable and plannable requirement through dialogue with the user. However, there is no need to pursue perfection excessively or get stuck in constant questioning.

# Specific Requirements
- The requirement must be clear and executable.
- You are only responsible for clarifying requirements with the user. As for whether the information or documents provided by the user are true or usable, you do not need to make judgments.
- For vague questions, if the user supplements with documents or links, the requirement shall be directly deemed sufficiently clear.
- When the current requirement is clear, you must give an refined objective in order to guide the planner.
- When user provides link or file path that can refer to the information, you must add it to the json output, make sure it is a valid url or file path.
- You must add the source reference to the json output in the form of a list of ResourceReference objects, URI to the source of must be a valid url or file path.
- Each ResourceReference object must have a description and a URI to the source of the information. The URI should be a valid url or file path.
- If the user provides multiple links or file paths, you must add them to the json output in the form of a list of ResourceReference objects.
- The type of each ResourceReference object must be 'from_user'.

# project directory
- project directory path(PROJECT_DIR): {PROJECT_DIR}


# Output
JSON format
"""

class ClaimerAgent:
    def __init__(self, notifier: Notifier, context_manager: ContextManager):
        self.messages = []
        # prompt = DEFAULT_INSTRUCTION.format(access_knowledgeDB())
        prompt = DEFAULT_INSTRUCTION.format(PROJECT_DIR=context_manager.get_project_dir())
        self.notifier = notifier
        self.context_manager = context_manager
        agent_id, channel = self.context_manager.get_consistent_agent_identity("Claimer")
        if agent_id is not None and channel:
            self.agent_id = agent_id
            self.identity = channel.rsplit("_main", 1)[0]
            if channel not in self.context_manager.dialogue_history:
                self.context_manager.add_active_subagent(self.agent_id, channel, dump=False)
        else:
            self.agent_id = self.context_manager.obtain_id(dump=False)
            self.identity = f"Claimer_{self.agent_id}"
            self.context_manager.register_consistent_subagent(self.agent_id, self.identity + "_main", "Claimer", dump=False)
            self.append_message({"role": "system", "content": prompt}, channel=self.identity + "_main", dump=False)
        
    def append_message(self, message: dict, channel: str | List[str] = None, usage: dict = None, dump: bool = True):
        """
        Append a message to the message list of the channel and current agent message list.
        Args:
            message (dict): The message to append.
            channel (str, optional): The channel to append the message to. Defaults to None.
        """
        if channel is None:
            channel = self.identity + "_main"
        # self.messages.append(message)
        self.context_manager.add_dialogue(self.agent_id, channel, [message | {"timestamp": datetime.now().timestamp()} | {"usage": usage}], dump=dump)

    @observe(
        name="claimer",
        span_type="claimer_span",
        process_outputs=claimer_process_output,
    )
    def run(self, query: str):
        if os.environ.get("AUTOMAS_ENABLE_OBSERVE", "0") == "1":
            QA = self.context_manager.get_active_qa("claimer")
        else:
            QA = []
        self.context_manager.set_active_qa("claimer", QA, dump=False)
        print("=====ClaimerAgent Started=====")
        try:
            if self.context_manager.get_available_resources():
                formatted_available_resources = self.context_manager.get_formatted_available_resources()
                self.append_message({"role": "user", "content": f"当前可用资源：\n {formatted_available_resources}"}, channel=[self.identity + "_main", "user"], dump=False) # 这里可能后续需要改，会把所有资源加入消息历史，可能会很长，至少不应该发到user信道被planner接受
            self.append_message({"role": "user", "content": query}, channel=[self.identity + "_main", "user"], dump=True)
            self._prepare_context()
            finish_reason, resp, usage = llm_call_json_schema(messages=self.messages, tools=[], jsonSchema="Claimer")
            if finish_reason == "error":
                raise RuntimeError(resp.content)
            resp = resp.parsed
            print(f'Finish Reason: {finish_reason}')
            while resp.need_more_info:
                first_dump_after_llm = True
                i = 0
                for model_query in resp.contents:
                    i += 1
                    model_query = model_query.query
                    print(f'Model query: {model_query} | ({i} / {len(resp.contents)})')
                    user_resp = self.notifier.call_user(model_query, invoker_agent_id=self.agent_id, in_channel=self.identity + "_main", out_channel="user")
                    self.append_message({"role": "assistant", "content": model_query}, channel=self.identity + "_main", dump=first_dump_after_llm)
                    first_dump_after_llm = False
                    self.append_message({"role": "user", "content": user_resp}, channel=self.identity + "_main", dump=(i == len(resp.contents)))
                    QA.append({"claimer": model_query, "user": user_resp})
                    self.context_manager.set_active_qa("claimer", QA, dump=False)
                self._prepare_context()
                finish_reason, resp, usage = llm_call_json_schema(messages=self.messages, tools=[], jsonSchema="Claimer")
                if finish_reason == "error":
                    raise RuntimeError(resp.content)
                resp = resp.parsed
            print(f"Source reference: \n {resp.resource_reference}")
            print(f"Refined objective: \n {resp.refined_objective}")
            for resource_ref in resp.resource_reference:
                self.append_message({"role": "user", "content": f"可用资源描述：{resource_ref.description} | 资源URI: {resource_ref.URI} | 资源来源类型(type): {resource_ref.type}"}, channel=[self.identity + "_main", "user"], dump=False)
                self.context_manager.add_available_resources({resource_ref.description: resource_ref}, dump=False)
            print("=====ClaimerAgent Finished=====")
            self.context_manager.is_clarified = True
            self.append_message({"role": "user", "content": f"现在的目标是：{resp.refined_objective}"}, channel=[self.identity + "_main", "user"], dump=False)
            self.context_manager.update_overall_goal(resp.refined_objective, dump=True)
            qa_snapshot = list(QA)
            return {
                "Refined_objective": resp.refined_objective,
                "resource_reference": resp.resource_reference,
                "total_usage": usage,
                "QA": qa_snapshot
            }
        finally:
            self.context_manager.clear_active_qa("claimer", dump=False)
            QA.clear()
            self.context_manager._auto_dump("claimer_exit", {"agent_id": self.agent_id})
        
    def _prepare_context(self):
        self.messages = self.context_manager.get_dialogue(invoker_channel=self.identity + "_main", filter=[self.identity + "_main"], formatted=False)
