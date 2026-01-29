from resources.tools.persistent_shell import PersistentShell


class ToolExecuter:
    def __init__(self):
        self.tools_desc_map = {}
        self.shell = PersistentShell()
        self.shell.create_terminal()
        self.tools_desc_map["command"] = {
            "type": "function",
            "function": {
                "name": "command",
                "description": "执行shell命令",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "command": {
                            "type": "string",
                            "description": "shell命令"
                        }
                    },
                    "required": ["command"]
                }
            }
        }
    
    def call(self, tool_name: str, args: dict):
        if tool_name == "command":
            return self.shell.execute_command(args["command"])
        return f"Tool {tool_name} not found"
    
    def get_tool(self, tool_name: str):
        return self.tools_desc_map[tool_name]