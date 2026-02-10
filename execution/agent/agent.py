from control.context_manager import ContextManager
from resources.tools.persistent_shell import PersistentShell
from resources.tools.skill_tool import get_skill_list
import json
from resources.tools.tool_executer import ToolExecuter
from llm.llm import llm_call, llm_call_json_schema
from .prompt import render
from typing import Dict, Any
from llm.json_schemas import SubmitMessage

DEFAULT_SUBMIT_PROMPT = """
# Role 
You are an assistant specialized in reporting task execution results, serving task management scenarios. Your core responsibility is to extract key information from task execution data and generate structured reporting content.

# Core Rules
- **Mandatory Actions**: You must extract the following from task execution data:
  - The name of the currently executing task
  - Task summary
  - Task status (strictly limited to one of four values: "pending", "completed", "stopped", or "cancelled")
  - A complete list of resources created during execution
- **Constraints**:
  - Task status must strictly match one of the four specified values; custom status values are prohibited
  - The resource list must comprehensively include all created resources without omission

# Output format
JSON format

Now, please generate the task execution results according to previous chat history.
"""



class Agent:
    def __init__(self, instruction: Dict[str, Any], tool_name_list: list, tool_executer: ToolExecuter, context_manager: ContextManager, shell: PersistentShell=None):
        self.instruction = instruction
        self.tool_name_list = tool_name_list
        self.tool_executer = tool_executer 
        self.context_manager = context_manager
        self.shell = shell
        self.messages = []
        prompt = render(**instruction)
        print(f"agent system prompt: {prompt}")
        self.messages.append({"role": "system", "content": prompt})

    def run(self, query: str):
        self.messages.append({"role": "user", "content": query})
        tools = []
        for tool_name in self.tool_name_list:
            tools.append(self.tool_executer.get_tool(tool_name))    
        while True:
            finish_reason, resp_msg = llm_call(self.messages, tools)
            if finish_reason != "tool_calls":
                content = resp_msg.content
                self.messages.append({"role": "assistant", "content": content})
                self.messages.append({"role": "user", "content": DEFAULT_SUBMIT_PROMPT})
                try:
                    finish_reason, resp_msg = llm_call_json_schema(self.messages, [], "Submit")
                    resources = {}
                    for resource in resp_msg.resource_reference:
                        resources[resource.description] = resource
                    print(f"submit {resp_msg.task_name}: \n {resp_msg.task_summary} \n status: {resp_msg.task_status}")
                    print(f"resources: {resources}")
                    self.context_manager.submit_sub_objective(resp_msg.task_summary, resp_msg.task_status, resources)
                    return content
                except Exception as e:
                    print(f"submit {self.messages[-1]} \n error: {e}")
                    error_summary = f"Error when submitting task execution results, error message: {e}"
                    self.context_manager.submit_sub_objective(error_summary, "pending", {})
                    return content
            self.messages.append(resp_msg.model_dump())
            tool_call = resp_msg.tool_calls[0]
            tool_name = tool_call.function.name
            tool_args = json.loads(tool_call.function.arguments)
            tool_result = self.tool_executer.call(tool_name, tool_args)
            self.messages.append(
                {"role": "tool", "content": tool_result, "tool_call_id": tool_call.id, "tool_name": tool_name}
            )
