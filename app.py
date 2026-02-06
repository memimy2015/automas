from llm.json_schemas import ResourceReference
from control.context_manager import ContextManager
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
# progress_manager = ProgressManager()
context_manager = ContextManager()
notifier = Notifier(context_manager)

# for test only
context_manager.add_available_resources({"公司信息，包含周报公司名称、汇报时间周期及核心内容模块": ResourceReference(description="公司信息，包含周报公司名称、汇报时间周期及核心内容模块", pointer="https://www.my_company.com/report", type="from_memorybase")})
context_manager.add_available_resources({"需要解决的题目截图": ResourceReference(description="需要解决的题目截图", pointer="image.png", type="from_memorybase")})


# agent = Agent(instruction="You are a helpful assistant.", tool_name_list=["command", "write_tmp_file", "read_tmp_file"], tool_executer=tool_executer, shell=shell)
claim_agent = ClaimerAgent(notifier, context_manager)
plan_agent = PlannerAgent(context_manager, notifier)
sys_prompt, msg = claim_agent.run(TEST_CASE_4)
_, msg = plan_agent.run()

while True:
    query = input("模拟agent结果:\n")
    if query == "exit":
        break
    plan_agent.run()
    