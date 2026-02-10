from resources.tools.progress_operation import submit
from resources.tools.progress_operation import update_progress
from resources.tools.persistent_shell import PersistentShell
from resources.tools.file_operation import write_file, read_file
from resources.tools.proactive_query import call_user



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
        
        self.tools_desc_map['update_progress'] = {
            "type": "function",
            "function": {
                "name": "update_progress",
                "description": "更新当前正在执行的子任务的进度，也可以说是对里程碑事件的记录，例如中间步骤得到成果，或者是出现错误信息。当你觉得目前任务执行出现了这类信息时，可以调用此函数记录下当前的进度。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "info": {
                            "type": "string",
                            "description": "执行的子任务的进度信息，也可以说是对里程碑事件的记录，例如中间步骤得到成果，或者是出现错误信息，描述不需要太细致。"
                        }
                    },
                    "required": ["info"]
                }
            }
        }
        
        self.tools_desc_map['submit'] = {
            "type": "function",
            "function": {
                # 工具函数名，必须和实际函数名一致
                "name": "submit",
                # 工具功能描述，让模型理解该函数的作用
                "description": "提交任务结果的工具，用于向系统上报指定子任务（sub-objective）的完成情况、总结信息及相关附件文件。注意！这个方法只能在本次子任务所有内容执行完毕时执行，以此记录下子任务的完成情况，并且上报。因此，这个方法只能调用一次，但是必须调用，来更新这个子任务的状态。",
                # 函数入参规范，严格匹配参数类型和含义
                "parameters": {
                    "type": "object",
                    "properties": {
                        "task_name": {
                            "type": "string",
                            "description": "任务名称，唯一标识本次提交的任务，需与任务创建时的名称保持一致"
                        },
                        "task_summary": {
                            "type": "string",
                            "description": "任务完成总结，简要描述任务的执行过程、结果、关键步骤或结论"
                        },
                        "task_status": {
                            "type": "string",
                            "description": "任务状态，可选值为pending、completed、stopped、cancelled，你需要根据任务执行情况选择合适的状态"
                        },
                        "resources": {
                            "type": "array",
                            "description": "在执行本次子任务（sub-objective）时，由模型新创建的相关资源列表，每个元素为描述资源信息的字典",
                            # 数组元素为Dict[str, str]，这里定义为ResourceReference对象所需的字段
                            "items": {
                                "type": "object",
                                "description": "单个资源的信息字典，包含资源的关键标识/属性",
                                "properties": {
                                    # 以下为通用资源属性示例，可根据你的实际业务需求增删/修改key
                                    "description": {
                                        "type": "string",
                                        "description": "关于新建资源的描述信息"
                                    },
                                    "URI": {
                                        "type": "string",
                                        "description": "资源的URI地址，如文件路径、网页URL等"
                                    },
                                    "type": {
                                        "type": "string",
                                        "description": "资源的类型，如from_memorybase、from_user、from_agent等，如果是你创建的文件，就标志为from_agent，否则根据提供给你的资源类型信息按原样填写"
                                    }
                                },
                                # 若资源字典有**必填key**，可在此处声明，无则删除该字段
                                "required": ["description", "URI", "type"]
                            }
                        }
                    },
                    # 函数核心必填参数，不可省略
                    "required": ["task_name", "task_summary", "task_status", "resources"]
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
    
    def call(self, tool_name: str, args: dict):
        if tool_name == "command":
            return self.shell.execute_command(args["command"])
        elif tool_name == "write_tmp_file":
            return write_file(args["file_path"], args["content"])
        elif tool_name == "read_tmp_file":
            return read_file(args["file_path"])
        elif tool_name == "update_progress":
            return update_progress(args["info"])
        elif tool_name == "submit":
            return submit(args["task_name"], args["task_summary"], args["task_status"], args["resources"])
        elif tool_name == "call_user":
            return call_user(args["query"])
        return f"Tool {tool_name} not found"
    
    def get_tool(self, tool_name: str):
        return self.tools_desc_map[tool_name]