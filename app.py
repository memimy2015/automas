from execution.agent.agent import Agent
from resources.tools.tool_executer import ToolExecuter
from resources.tools.persistent_shell import PersistentShell
from resources.tools.file_operation import write_file, read_file


shell = PersistentShell()
tool_executer = ToolExecuter()
agent = Agent(instruction="You are a helpful assistant.", tool_name_list=["command", "write_tmp_file", "read_tmp_file"], tool_executer=tool_executer, shell=shell)
res = agent.run("https://mp.weixin.qq.com/s/qbXm1Vq7dc_2KPOJerZUqw 对网页内容做总结，提取摘要，输出pdf文件，格式美观")
print(res)