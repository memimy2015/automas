from resources.tools.progress_operation import update_progress
from resources.tools.persistent_shell import PersistentShell
from resources.tools.file_operation import write_file, read_file
from resources.tools.proactive_query import call_user
import json
import os



class ToolExecuter:
    def __init__(self):
        self.tools_desc_map = {}
        self.shell = PersistentShell()
        self.shell.create_terminal()
        self.mock_enabled = os.getenv("IS_MOCK_ENABLED", "0") == "1"
        self.mock_map = self._load_mock_map()
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
        
        self.tools_desc_map['update_progress'] = {
            "type": "function",
            "function": {
                "name": "update_progress",
                "description": "更新当前正在执行的子任务的进度，也可以说是对里程碑事件的记录，例如中间步骤得到成果，或者是出现错误信息。当你觉得目前任务执行出现了这类信息时，可以调用此函数记录下当前的进度。但是必须保证信息精确简洁。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "info": {
                            "type": "string",
                            "description": "执行的子任务的进度信息，也可以说是对里程碑事件的记录，例如中间步骤得到成果，或者是出现错误信息，必须保证信息精确简洁。"
                        }
                    },
                    "required": ["info"]
                }
            }
        }
        
        self.tools_desc_map['call_user'] = {
            "type": "function",
            "function": {
                "name": "call_user",
                "description": "调用用户交互的工具，用于向用户获取更多信息。当你认为目前的情况需要得到用户的许可或者指挥，就使用这个方法。比如遇到权限问题时、需要用户确认某个关键操作时，又或者是遇到严重错误等，可能需要用户进行后续计划的判断的情况，此时一定要请求用户的回答。其他情况下尽量不要使用这个工具打扰用户，尤其是问候类的语句。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "发送给用户的信息，用户需要根据这个信息进行确认或操作。如果这个信息需要用户做出选择，你最好提供几个选择给用户参考。尤其是遇到严重错误无法完成任务时，必须请求用户确认是否继续执行后续操作或者提供信息来解决错误，为此请在发给用户的提问中包含必要的信息，例如确认操作、拒绝操作、提供额外信息、解决建议等。"
                        }
                    },
                    "required": ["query"]
                }
            }
        }

    def _load_mock_map(self) -> dict:
        if not self.mock_enabled:
            return {}
        current_file_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(os.path.dirname(current_file_dir))
        mock_path = os.path.join(project_root, "mock", "tool_mock.json")
        if not os.path.exists(mock_path):
            return {}
        with open(mock_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _mock_key(self, tool_name: str, args: dict) -> str:
        payload = json.dumps(args, ensure_ascii=False, sort_keys=True)
        return f"{tool_name}:{payload}"
    
    def call(self, tool_name: str, args: dict):
        if self.mock_enabled:
            key = self._mock_key(tool_name, args)
            if key in self.mock_map:
                return self.mock_map[key]
            print(f"MOCK_NOT_FOUND: {tool_name}")
            return f"MOCK_NOT_FOUND: {tool_name}"
        if tool_name == "command":
            return self.shell.execute_command(args["command"])
        elif tool_name == "write_tmp_file":
            return write_file(args["file_path"], args["content"])
        elif tool_name == "read_tmp_file":
            return read_file(args["file_path"])
        elif tool_name == "update_progress":
            return update_progress(args["info"])
        # elif tool_name == "submit":
        #     return submit(args["task_name"], args["task_summary"], args["task_status"], args["resources"])
        elif tool_name == "call_user":
            return call_user(args["query"], args["invoker_agent_id"], args["in_channel"], args["out_channel"])
        return f"Tool {tool_name} not found"
    
    def get_tool(self, tool_name: str):
        return self.tools_desc_map[tool_name]
    
    def list_tools(self):
        return self.tools_desc_map.keys()
