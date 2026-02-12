from execution.agent.agent import Agent
from resources.tools.tool_executer import ToolExecuter
from resources.tools.persistent_shell import PersistentShell
from resources.tools.skill_tool import get_skill_list
from control.context_manager import ContextManager



shell = PersistentShell()
tool_executer = ToolExecuter()
skill_list = get_skill_list()
instructions = {
    "role_setting": "You are a helpful assistant.",
    "task_background": "",
    "sub_objective": "",
    "task_specification": "",
    "skills": skill_list
}
agent = Agent(instruction=instructions, tool_name_list=["command", "write_tmp_file", "read_tmp_file"], tool_executer=tool_executer, context_manager=ContextManager(), shell=shell)
print(agent.run("https://mp.weixin.qq.com/s/qbXm1Vq7dc_2KPOJerZUqw 对网页内容做总结，提取摘要，输出pdf文件，格式美观。"))