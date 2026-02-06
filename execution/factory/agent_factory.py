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
{}
# Current Sub-Objective
This is the current sub-objective that needs to be achieved, you must focus on it and give the role and task specification for the sub-objective in order to help the model to execute the sub-objective successfully:
{}

# Output format
JSON format

"""

class AgentFactory():
    def __init__(self, context_manager: ContextManager, default_tool_name_list: list, tool_executer: ToolExecuter, shell: PersistentShell=None):
        self.context_manager = context_manager
        self.default_tool_name_list = default_tool_name_list
        self.tool_executer = tool_executer
        self.shell = shell
        self.current_subtask_index, self.current_subtask_step_index = self.context_manager._get_current_subtask_index()
        self.messages = [{"role": "system", "content": DEFAULT_INSTRUCTION.format("placeholder", "placeholder")}]
        self.messages.append({"role": "user", "content": "Placeholder"})

    def create_agent(self, instruction: Dict[str, Any], tool_name_list: list = None) -> Agent:
        if tool_name_list is None:
            tool_name_list = self.default_tool_name_list
        return Agent(instruction, tool_name_list, self.tool_executer, self.shell)

    def run(self, tool_name_list: list = None) -> Agent:
        if tool_name_list is None:
            tool_name_list = self.default_tool_name_list
        formatted_subtask = self.context_manager.get_formatted_subtask(self.current_subtask_index)
        formatted_subtask_step = self.context_manager.get_formatted_subtask_step(self.current_subtask_index, self.current_subtask_step_index)
        self.messages[0] = {"role": "system", "content": DEFAULT_INSTRUCTION.format(formatted_subtask, formatted_subtask_step)}
        self.messages[1] = {"role": "user", "content": "Now give your suggested role and task specification for prompt of sub-objective."}
        _, resp = llm_call_json_schema(self.messages, [], "PromptEngineer")
        instrction = {
            "role_setting": resp.role_setting,
            "task_specification": resp.task_specification,
            "skills": get_skill_list(),
            "task_background": formatted_subtask,
            "current_sub_objective": formatted_subtask_step,
        }
        return self.create_agent(instrction, tool_name_list)
