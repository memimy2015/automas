from control.context_manager import ContextManager
from resources.tools.persistent_shell import PersistentShell
from resources.tools.skill_tool import get_skill_list
import json
from resources.tools.tool_executer import ToolExecuter
from llm.llm import llm_call, llm_call_json_schema
from llm.json_schemas import ProacvtiveQuery, ClaimerSchema
from execution.agent.prompt import render
from .notifier import Notifier

def access_knowledgeDB():
    return "None"

DEFAULT_INSTRUCTION = """
# 角色设定
你是文件提取专员，服务于用户需求响应系统，核心职责是从给定上下文里精准定位并提取用户完成目标所需的全部文件。

# 操作准则
## 必须执行
1. 若用户目标明确提及文件类型，优先匹配对应类型的文件；
2. 若规划器任务中指定了参考文件，必须纳入提取范围；
3. 子agent输出的文件需全部检查，符合用户目标的要提取。
4. 确保信息准确，不能有错误或遗漏。

## 禁止行为
1. 不得提取与用户目标、规划器任务无关的文件；
2. 不能遗漏上下文里明确关联的文件；
3. 禁止对文件内容做主观修改，需保持原始名称。

# Output

1. 结构框架：先列核心资源，再列辅助资源；
2. 使用markdown格式输出，给出资源名，资源URI以及资源简介；
"""

class OutputCollectorAgent:
    def __init__(self, notifier: Notifier, context_manager: ContextManager):
        self.messages = []
        prompt = DEFAULT_INSTRUCTION
        self.messages.append({"role": "system", "content": prompt})
        self.notifier = notifier
        self.context_manager = context_manager

    def run(self):
        self.messages.append({"role": "user", 
                              "content": f"根据之前的信息，找出我一开始提出的要求所对应的资源，需要名字、描述和URI，确保信息准确，我一开始的要求是：{self.context_manager.overall_goal}"})
        return self.messages[0], self.messages[1:]
        
        