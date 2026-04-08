from resources.tools.progress_operation import update_progress
from resources.tools.persistent_shell import PersistentShell
from resources.tools.file_operation import write_file, read_file, load_full_skill_description
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

        self.tools_desc_map["write_file"] = {
            "type": "function",
            "function": {
                "name": "write_file",
                "description": "写入或追加文本文件内容（txt/html/markdown/py等）。mode=write 会覆盖写入；mode=append 会在文件末尾追加，最好在文件已经存在时使用追加。目录不存在会自动创建。",
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
                        },
                        "mode": {
                            "type": "string",
                            "description": "写入模式：write 覆盖写入；append 追加写入",
                            "enum": ["write", "append"]
                        }
                    },
                    "required": ["file_path", "content"]
                }
            }
        }

        self.tools_desc_map["read_file"] = {
            "type": "function",
            "function": {
                "name": "read_file",
                "description": "读取文件内容：支持 txt/html/markdown/py 等文本文件；支持本地图片文件读取；支持图片 URL 读取；对于大小超过10MB的图片，会自动尝试压缩。",
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

        self.tools_desc_map["load_full_skill_description"] = {
            "type": "function",
            "function": {
                "name": "load_full_skill_description",
                "description": "读取技能文件描述 skills.md 的完整内容",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "skills.md 文件路径"
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
                "description": "记录可验证的，对于用户有意义的，执行记录/里程碑/状态变化（包括但不限于行为、决策、产物生成、关键结论、错误与重试、阻塞原因、外部依赖完成等）。不要记录中间推理、草稿、闲聊或长篇过程描述。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "info": {
                            "type": "string",
                            "description": "一条简短、可验证的事实记录：要做或者做了什么，如果有的话，还要简单说明结果是什么！；必要时附路径/错误摘要/错误码。避免敏感信息与长段落。"
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
                "description": "向用户发起一次交互请求，仅在必须由用户提供信息/完成外部验证时使用。不要用它发送中间推理、草稿或进度汇报，更不要用来询问skill和tool能不能使用！。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "发给用户的请求内容，必须简短明确，但是格式要美观，推荐使用markdown格式：说明需要用户做什么/提供什么信息/确认什么决策，并给出可选项或可复制的输入格式。不要包含中间推理或无关背景。"
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
        elif tool_name == "write_file":
            return write_file(args["file_path"], args["content"], args.get("mode", "write"))
        elif tool_name == "read_file":
            return read_file(args["file_path"])
        elif tool_name == "load_full_skill_description":
            return load_full_skill_description(args["file_path"])
        elif tool_name == "update_progress":
            return update_progress(args["info"])
        # elif tool_name == "submit":
        #     return submit(args["task_name"], args["task_summary"], args["task_status"], args["resources"])
        elif tool_name == "call_user":
            return call_user(args["query"], args["invoker_agent_id"], args["in_channel"], args["out_channel"])
        return f"Tool {tool_name} not found"

    def build_tool_result_messages(self, tool_name: str, tool_args: dict, tool_result, tool_call_id: str):
        if tool_name == "read_file" and self._is_read_file_image_payload(tool_result):
            file_path = ""
            if isinstance(tool_args, dict):
                file_path = tool_args.get("file_path") or ""
            content = f"图片内容已成功读取: {file_path}" if file_path else "图片内容已成功读取"
            return [
                {"role": "tool", "content": content, "tool_call_id": tool_call_id, "tool_name": tool_name},
                {"role": "user", "content": tool_result},
            ]
        return [{"role": "tool", "content": tool_result, "tool_call_id": tool_call_id, "tool_name": tool_name}]

    def _is_read_file_image_payload(self, tool_result) -> bool:
        if not isinstance(tool_result, list):
            return False
        for item in tool_result:
            if not isinstance(item, dict):
                continue
            if item.get("type") == "image_url":
                image_url = item.get("image_url")
                if isinstance(image_url, dict) and image_url.get("url"):
                    return True
        return False
    
    def get_tool(self, tool_name: str):
        return self.tools_desc_map[tool_name]
    
    def list_tools(self):
        return self.tools_desc_map.keys()
