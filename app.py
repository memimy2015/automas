from execution.agent.agent import Agent
from resources.tools.tool_executer import ToolExecuter
from resources.tools.persistent_shell import PersistentShell


shell = PersistentShell()
tool_executer = ToolExecuter()
agent = Agent(instruction="You are a helpful assistant.", tool_name_list=["command"], tool_executer=tool_executer, shell=shell)
res = agent.run("https://mp.weixin.qq.com/s/qbXm1Vq7dc_2KPOJerZUqw 总结一下这个内容")
print(res)