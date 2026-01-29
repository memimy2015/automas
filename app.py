from agent.agent import Agent
from resources.tools.tool_executer import ToolExecuter
from resources.tools.persistent_shell import PersistentShell


shell = PersistentShell()
tool_executer = ToolExecuter()
agent = Agent(instruction="You are a helpful assistant.", tool_name_list=["command"], tool_executer=tool_executer, shell=shell)
res = agent.run("帮我看一下当前目录都有哪些文件")
print(res)