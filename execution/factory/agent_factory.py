from operator import index
from webbrowser import get
from llm.json_schemas import FactoryOutput
from llm.llm import llm_call_json_schema
from control.context_manager import ContextManager
from execution.agent.agent import Agent
from resources.tools.persistent_shell import PersistentShell
from resources.tools.skill_tool import get_skill_list
import json
from resources.tools.tool_executer import ToolExecuter
from llm.llm import llm_call
from typing import Dict, Any
from miscellaneous.cozeloop_preprocess import agent_factory_process_output
from miscellaneous.observe import observe
import os
from prompt_manager import get_prompt_manager
from datetime import datetime


DEFAULT_INSTRUCTION = """
# Role
You are a Dynamic Prompt Engineer belonging to the AI Task Execution Support Team. 
Your core responsibility is to generate precise role and task specification prompts for large models based on the user-provided overall task background and the current sub-objective to be executed, ensuring the prompt aligns with the overall task objective and focuses on the implementation requirements of the sub-objective.

# Caution
Please ensure the role and task specification are precise and focused on the implementation requirements of the sub-objective.
Please avoid using generic terms or abstract concepts.
Please use specific terms or concepts to describe the sub-objective.
If there are available resources according to the task background, please refer them explicitly in the prompt.

# Task Background
This is a structured format of the task background, containing every step of the task execution process and some available resources:
{task_background}
# Current Sub-Objective
This is the current sub-objective that needs to be achieved, you must focus on it and give the role and task specification for the sub-objective in order to help the model to execute the sub-objective successfully:
{current_sub_objective}

# Output format
JSON format

"""

class AgentFactory():
    def __init__(self, context_manager: ContextManager, default_tool_name_list: list, tool_executer: ToolExecuter, shell: PersistentShell=None):
        self.context_manager = context_manager
        self.default_tool_name_list = default_tool_name_list
        self.tool_executer = tool_executer
        self.shell = shell
        pm = get_prompt_manager()
        self.messages = [{"role": "system", "content": pm.render("agent_factory.system", DEFAULT_INSTRUCTION, None, task_background="placeholder", current_sub_objective="placeholder", current_date=datetime.now().strftime("%Y年%m月%d日"))}]
        self.messages.append({"role": "user", "content": "Placeholder"})

    def create_agent(self, instruction: Dict[str, Any], tool_name_list: list = None) -> Agent:
        if tool_name_list is None:
            tool_name_list = self.default_tool_name_list
        return Agent(instruction, tool_name_list, self.tool_executer, self.context_manager, self.shell)
    
    @observe(
        name="agent_factory",
        span_type="agent_factory_span",
        process_outputs=agent_factory_process_output,
    )
    def run(self, tool_name_list: list = None) -> Agent:
        try:
            print("AgentFactory Creating New Agent")
            self.current_subtask_index, self.current_subtask_step_index = self.context_manager._get_current_indices()
            if tool_name_list is None:
                tool_name_list = self.default_tool_name_list
            current_subtask = self.context_manager.get_subtask(self.current_subtask_index)
            current_subtask_step = self.context_manager.get_subtask_step(self.current_subtask_index, self.current_subtask_step_index)
            formatted_subtask = self.context_manager.get_formatted_subtask(current_subtask, self.current_subtask_index + 1)
            formatted_subtask_step = self.context_manager.get_formatted_subtask_step(current_subtask_step, self.current_subtask_index + 1, self.current_subtask_step_index + 1)
            formatted_plan = self.context_manager.get_formatted_plan(self.context_manager.get_task_status()[0])
            pm = get_prompt_manager()
            self.messages[0] = {"role": "system", "content": pm.render("agent_factory.system", DEFAULT_INSTRUCTION, None, task_background=formatted_plan, current_sub_objective=formatted_subtask_step, current_date=datetime.now().strftime("%Y年%m月%d日"))}
            self.messages[1] = {"role": "user", "content": "Now give your suggested role and task specification for prompt of sub-objective."}
            
            
            did_llm_call = True
            if os.getenv("IS_DEBUG_ENABLED", "1") == "1" and self.context_manager.is_executing:
                resp = self.context_manager.latest_agent_factory_output
                print(f"AgentFactory loaded last output: {resp.model_dump_json(indent=2)}")
                did_llm_call = False
            else:
                finish_reason, resp, usage = llm_call_json_schema(messages=self.messages, tools=[], jsonSchema="PromptEngineer")
                if finish_reason == "error":
                    raise RuntimeError(resp.content)
                resp = resp.parsed
                print(f"AgentFactory output: {resp.model_dump_json(indent=2)}")
            instruction = {
                "role_setting": resp.role_setting,
                "task_specification": resp.task_specification,
                "skills": get_skill_list(),
                "task_background": "None",
                "sub_objective": formatted_subtask_step,
            }
            self.context_manager.record_agent_factory_output(resp, dump=did_llm_call)
            print("AgentFactory Created New Agent")
            return {
                "agent": self.create_agent(instruction, tool_name_list),
                "instruction": instruction,
            }
        finally:
            self.context_manager._auto_dump(
                "agent_factory_exit",
                {
                    "current_subtask_index": getattr(self, "current_subtask_index", None),
                    "current_subtask_step_index": getattr(self, "current_subtask_step_index", None),
                },
            )
