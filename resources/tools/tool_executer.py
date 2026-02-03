from resources.tools.persistent_shell import PersistentShell
from resources.tools.file_operation import write_file, read_file


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

        self.tools_desc_map["write_tmp_file"] = {
            "type": "function",
            "function": {
                "name": "write_tmp_file",
                "description": "写入临时文件，包括txt，html，markdown，py等文本内容，主要是为了后续的shell命令执行。如果需要修改文件内容，需要先删除文件，再重新写入完整内容。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "文件路径"
                        },
                        "content": {
                            "type": "string",
                            "description": "文件内容"
                        }
                    },
                    "required": ["file_path", "content"]
                }
            }
        }

        self.tools_desc_map["read_tmp_file"] = {
            "type": "function",
            "function": {
                "name": "read_tmp_file",
                "description": "读取临时文件，包括txt，html，markdown，py等文本内容，主要是为了后续的shell命令执行",    
                "parameters": {
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "文件路径"
                        }
                    },
                    "required": ["file_path"]
                }
            }
        }
    
    def call(self, tool_name: str, args: dict):
        if tool_name == "command":
            return self.shell.execute_command(args["command"])
        elif tool_name == "write_tmp_file":
            return write_file(args["file_path"], args["content"])
        elif tool_name == "read_tmp_file":
            return read_file(args["file_path"])
        return f"Tool {tool_name} not found"
    
    def get_tool(self, tool_name: str):
        return self.tools_desc_map[tool_name]