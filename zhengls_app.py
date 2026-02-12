from execution.agent.agent import Agent
from resources.tools.tool_executer import ToolExecuter
from resources.tools.persistent_shell import PersistentShell
from resources.tools.skill_tool import get_skill_list


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
agent = Agent(instruction=instructions, tool_name_list=["command", "write_tmp_file", "read_tmp_file"], tool_executer=tool_executer, shell=shell)
print(agent.run("优先使用pptx技能，把tmp中的多个html文件转为一份ppt"))