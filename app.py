from execution.factory.agent_factory import AgentFactory
from llm.json_schemas import ResourceReference
from control.context_manager import ContextManager
from execution.agent.agent import Agent
from control.ClaimerAgent import ClaimerAgent
from control.PlannerAgent import PlannerAgent
from resources.tools.tool_executer import ToolExecuter
from resources.tools.persistent_shell import PersistentShell
from resources.tools.file_operation import write_file, read_file
from control.notifier import Notifier
from resources.tools.console_input import get_input

TEST_CASE_1="https://mp.weixin.qq.com/s/qbXm1Vq7dc_2KPOJerZUqw 对网页内容做总结，提取摘要，输出pdf文件，格式美观"
TEST_CASE_2="我想去旅游，帮我做一下规划吧"
TEST_CASE_3="输出10个1"
TEST_CASE_4="我需要生成一份公司周报的ppt，用来在会议上演示" # Badcase 如果说信息在文件内的话就会不停的要求给文字内容，因为不能读取 - 已解决。
TEST_CASE_5="解决这道题" # badcase
TEST_CASE_6="https://zhuanlan.zhihu.com/p/1999034708332405397 对网页内容做总结，提取摘要，输出pdf文件，格式美观" # badcase
TEST_CASE_7="https://www.bilibili.com/read/cv9314580/?opus_fallback=1 总结一下网页的文字内容，然后给我展示一下M1的特性和性能，包括一些参数，输出为pdf文件，美观一点" 
TEST_CASE_8="https://aime.bytedance.net/chat?spaceId=adaf00f3-6168-4a58-aed4-bae54f4d02fd&source=0&order=6 浏览网页内的公开模板以及其中的内容，找出有关于office办公的以及飞书的相关操作的模板，并且整理出他们的模板名字放在markdown文件里给我看。我之后需要根据这些模板的名字搜索他们。"
TEST_CASE_9="https://news.ycombinator.com/item?id=45684134, 浏览网页信息，并且做一下汇总，尤其是关于claude的memory部分的分析，输出pdf文件，格式美观，同时整理一份markdown版本的。"
TEST_CASE_9="https://news.ycombinator.com/item?id=45684134, https://code.claude.com/docs/en/memory 浏览网页信息，并且做一下汇总，尤其是关于claude的memory部分的分析，把前一个网址中的用户讨论内容和后一个网址中的官方文档的内容匹配一下，输出pdf文件，格式美观，同时整理一份markdown版本的。对于前一个网址的总结文档我已经有一份markdown格式的了，你可能不需要直接看网址内容。"
TEST_CASE_10="""
# 需求
我现在在尝试根据openclaw，claude code和claude以及一些论文来构建多agent系统的长期记忆模块，我需要你阅读我提供的材料，包括网址和论文pdf，最后为每一个资料来源整理一份markdown文档，记录一下他的大概内容和主要思想，都是针对长期记忆构建这方面的。最后在汇总一下，被我额外输出一份markdown报告，并且给出你的建议。
对于图片信息，你可以忽略
# claude api
https://platform.claude.com/docs/en/agents-and-tools/tool-use/memory-tool
# claude code memory
https://code.claude.com/docs/en/memory
# openclaw
https://docs.openclaw.ai/concepts/memory
# open memory
https://github.com/CaviraOSS/OpenMemory
# essay pdf directory
/mnt/c/Users/Admin/Desktop/20260203/AIME/automas/essay
"""
# DEFAULT_TOOLS_LIST = ["command", "write_tmp_file", "read_tmp_file", "update_progress", "call_user"]

shell = PersistentShell()
tool_executer = ToolExecuter()
context_manager = ContextManager()
notifier = Notifier(context_manager)
DEFAULT_TOOLS_LIST = tool_executer.list_tools()
print(f"Available tools: {DEFAULT_TOOLS_LIST}")
# for test only
# context_manager.add_available_resources({"公司信息，包含周报公司名称、汇报时间周期及核心内容模块": ResourceReference(description="公司信息，包含周报公司名称、汇报时间周期及核心内容模块", URI="https://www.my_company.com/report", type="from_memorybase")})
# context_manager.add_available_resources({"需要解决的题目截图": ResourceReference(description="需要解决的题目截图", URI="image.png", type="from_memorybase")})



# agent = Agent(instruction="You are a helpful assistant.", tool_name_list=DEFAULT_TOOLS_LIST, tool_executer=tool_executer, shell=shell)
claim_agent = ClaimerAgent(notifier, context_manager)
plan_agent = PlannerAgent(context_manager, notifier)
agent_factory = AgentFactory(context_manager,DEFAULT_TOOLS_LIST, tool_executer, shell)
sys_prompt, msg = claim_agent.run(TEST_CASE_10)
is_accomplished = plan_agent.run()

while not is_accomplished:
    agent = agent_factory.run()
    resp = agent.run("执行刚刚给你的任务")
    print("=====Agent Response===== \n", resp)
    # 把当前子任务的执行反馈加入对话记录
    current_subtask_index, current_subtask_step_index = context_manager._get_current_indices()
    current_subtask = context_manager.get_subtask(current_subtask_index)
    current_subtask_step = context_manager.get_subtask_step(current_subtask_index, current_subtask_step_index)
    formatted_subtask_step = context_manager.get_formatted_subtask_step(current_subtask_step, current_subtask_index + 1, current_subtask_step_index + 1)
    context_manager.add_dialogue({"role": "assistant", "content": formatted_subtask_step + "\n Execution summary from agent: \n" + resp})
    
    print("=====Current Plan=====")
    print(context_manager.get_formatted_plan(context_manager.task_state))
    
    is_accomplished = context_manager.is_accomplished() or plan_agent.run()

print("All tasks accomplished.")
print("=====Overview=====")
task_plan = context_manager.task_state
print(context_manager.get_formatted_plan(task_plan))
    
