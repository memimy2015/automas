from resources.tools.persistent_shell import PersistentShell
import json
from resources.tools.tool_executer import ToolExecuter
from llm.llm import llm_call


class Agent:
    def __init__(self, instruction: str, tool_name_list: list, tool_executer: ToolExecuter, shell: PersistentShell=None):
        self.instruction = instruction
        self.tool_name_list = tool_name_list
        self.tool_executer = tool_executer 
        self.shell = shell
        self.messages = []

    def run(self, query: str):
        self.messages.append({"role": "system", "content": self.instruction})
        self.messages.append({"role": "user", "content": query})
        tools = []
        for tool_name in self.tool_name_list:
            tools.append(self.tool_executer.get_tool(tool_name))
        while True:
            finish_reason, resp_msg = llm_call(self.messages, tools)
            if finish_reason != "tool_calls":
                return resp_msg.content
            self.messages.append(resp_msg.model_dump())
            tool_call = resp_msg.tool_calls[0]
            tool_name = tool_call.function.name
            tool_args = json.loads(tool_call.function.arguments)
            tool_result = self.tool_executer.call(tool_name, tool_args)
            self.messages.append(
                {"role": "tool", "content": tool_result, "tool_call_id": tool_call.id}
            )