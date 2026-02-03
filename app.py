from execution.agent.agent import Agent
from control.ClaimerAgent import ClaimerAgent
from control.PlannerAgent import PlannerAgent
from resources.tools.tool_executer import ToolExecuter
from resources.tools.persistent_shell import PersistentShell
from resources.tools.file_operation import write_file, read_file
from control.notifier import Notifier
from control.progress_manager import ProgressManager

TEST_CASE_1="https://mp.weixin.qq.com/s/qbXm1Vq7dc_2KPOJerZUqw 对网页内容做总结，提取摘要，输出pdf文件，格式美观"
TEST_CASE_2="我想去旅游，帮我做一下规划吧"
TEST_CASE_3="输出10个1"
TEST_CASE_4="我需要生成一份公司周报的ppt，用来在会议上演示" # Badcase 如果说信息在文件内的话就会不停的要求给文字内容，因为不能读取。
TEST_CASE_5="解决这道题" # badcase

shell = PersistentShell()
tool_executer = ToolExecuter()
notifier = Notifier()
progress_manager = ProgressManager()
# agent = Agent(instruction="You are a helpful assistant.", tool_name_list=["command", "write_tmp_file", "read_tmp_file"], tool_executer=tool_executer, shell=shell)
claim_agent = ClaimerAgent(notifier)
plan_agent = PlannerAgent(progress_manager)
sys_prompt, msg = claim_agent.run(TEST_CASE_5)
_, msg = plan_agent.run("给出你的规划", prev_msg_list=msg)

while True:
    query = input("模拟agent结果:\n")
    if query == "exit":
        break
    plan_agent.run(query)
    