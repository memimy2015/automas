from control.SummarizerAgent import SummarizerAgent
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
import argparse
import os
from cozeloop import new_client, flush, get_span_from_context
from miscellaneous.observe import observe
from cozeloop.logger import set_log_level
import logging
from miscellaneous.cozeloop_preprocess import loop_process_output, step_process_output, step_process_input

logger = logging.getLogger(__name__)

TEST_CASES = {
    "TEST_CASE_1": "https://mp.weixin.qq.com/s/qbXm1Vq7dc_2KPOJerZUqw 对网页内容做总结，提取摘要，输出pdf文件，格式美观。制作PDF要使用pdf skill",
    "TEST_CASE_2": "我想去旅游，帮我做一下规划吧",
    "TEST_CASE_3": "输出10个1",
    "TEST_CASE_4": "我需要生成一份公司周报的ppt，用来在会议上演示",
    "TEST_CASE_5": "解决这道题",
    "TEST_CASE_6": "https://zhuanlan.zhihu.com/p/1999034708332405397 对网页内容做总结，提取摘要，输出pdf文件，格式美观",
    "TEST_CASE_7": "https://www.bilibili.com/read/cv9314580/?opus_fallback=1 总结一下网页的文字内容，然后给我展示一下M1的特性和性能，包括一些参数，输出为pdf文件，美观一点",
    "TEST_CASE_8": "https://aime.bytedance.net/chat?spaceId=adaf00f3-6168-4a58-aed4-bae54f4d02fd&source=0&order=6 浏览网页内的公开模板以及其中的内容，找出有关于office办公的以及飞书的相关操作的模板，并且整理出他们的模板名字放在markdown文件里给我看。我之后需要根据这些模板的名字搜索他们。",
    "TEST_CASE_9": "https://news.ycombinator.com/item?id=45684134, 浏览网页信息，并且做一下汇总，尤其是关于claude的memory部分的分析，输出pdf文件，格式美观，同时整理一份markdown版本的。",
    "TEST_CASE_10": "https://news.ycombinator.com/item?id=45684134, https://code.claude.com/docs/en/memory 浏览网页信息，并且做一下汇总，尤其是关于claude的memory部分的分析，把前一个网址中的用户讨论内容和后一个网址中的官方文档的内容匹配一下，输出pdf文件，格式美观，同时整理一份markdown版本的。对于前一个网址的总结文档我已经有一份markdown格式的了，你可能不需要直接看网址内容。",
    "TEST_CASE_11": """
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
}

# 已经完成
TEST_CASES["TEST_CASE_12"] = """
总结我的工作内容，生成一份工作报告pdf
报告模版及要求参考: /mnt/c/Users/Admin/Desktop/20260203/AIME/automas/testcase_resources/工作总结/个人周期报告/个人周期报告模版.pdf 
工作内容相关信息补充:
本地文件: /mnt/c/Users/Admin/Desktop/20260203/AIME/automas/testcase_resources/工作总结/个人周期报告
所有需要的信息都存放在这个文件夹下
"""

# 已经完成
TEST_CASES["TEST_CASE_13"] = """
总结工作内容，生成一份工作报告pdf
报告模版及要求参考: /mnt/c/Users/Admin/Desktop/20260203/AIME/automas/testcase_resources/工作总结/研发团队周期报告/研发团队周期报告模版.pdf 
工作内容相关信息补充:
本地文件: /mnt/c/Users/Admin/Desktop/20260203/AIME/automas/testcase_resources/工作总结/研发团队周期报告
所有需要的信息都存放在这个文件夹下
目前是Q3季度，关于Q4的内容都是规划
"""

# 已经完成
TEST_CASES["TEST_CASE_14"] = """
总结工作内容，生成一份工作报告pdf
报告模版及要求参考: /mnt/c/Users/Admin/Desktop/20260203/AIME/automas/testcase_resources/工作总结/项目方向报告/项目方向报告模板V2.pdf
工作内容相关信息补充:
本地文件: /mnt/c/Users/Admin/Desktop/20260203/AIME/automas/testcase_resources/工作总结/项目方向报告
所有需要的信息都存放在这个文件夹下
"""

# 已经完成
TEST_CASES["TEST_CASE_15"] = """
阅读论文: /mnt/c/Users/Admin/Desktop/20260203/AIME/automas/essay/Agentic-Memory_Learning-Unified-Long-Term-and-Short-Term-Memory-Management-for-LLM-Agents.pdf
并且查找阅读相关和相似论文，对比不同方法的优劣，总结为一篇PDF报告
"""

# 出错（planner输出json没通过校验），只差ppt生成
TEST_CASES["TEST_CASE_16"] = """
针对智能安防与大模型技术的结合，做一些技术和市场调研，生成PPT报告
"""

# 已经完成
TEST_CASES["TEST_CASE_17"] = """
我想要从杭州出发到西安旅游，5月1日出发，5月4日返程。人均消费1万元左右。帮我做一下行程规划。要包含交通、餐饮、住宿、景点，行程要足够细致，要按照半天为单位安排景点，要考虑景点和景点、景点和餐饮、景点和住宿之间的交通方式和距离。可以参考一些攻略。
"""

# 挂了，shell那边出现broken pipe问题，但是已经完成了一部分任务
TEST_CASES["TEST_CASE_18"] = """
阅读huggingface和modelscope里面关于大模型领域的热门论文，对论文进行解读，并且对里面的核心理念给出通俗易懂的解释，写入pdf文档。
前往 https://huggingface.co/papers ，切换到 Weekly 榜单，依次浏览排名前 10 的论文。对于每篇论文:
1. 总结论文摘要，记录标题和 URL。
2. 突出显示与 强化学习 相关的论文。
3. 最后将所有内容汇总成一份结构化报告，并按相关性排序。
"""

# 正在跑，小说写完了，但是后续任务计划绘制封面所以取消了
TEST_CASES["TEST_CASE_19"] = """
帮我写个小说，12章以内，下面是题材要求：
都市轻喜剧，主打“反套路合租”，聚焦性格反差极大的三个年轻人，在一间老小区的两居室里发生的一系列搞笑又温暖的日常。社恐慢热、爱钻牛角尖的会计林晚，被迫和两个“显眼包”室友合租——话痨爱折腾、干啥啥不行的创业未遂者江熠，以及看似高冷毒舌、实则爱管闲事的宠物医院助理苏冉。三人性格碰撞不断，从最初的互相嫌弃、鸡飞狗跳，到后来的彼此包容、互相搭救，没有狗血剧情，全是接地气的搞笑日常、细碎的温暖瞬间，主打轻松解压，贴合当代年轻人的合租生活，既有笑点又有共鸣，适合碎片化阅读和长期连载。
"""

# 挂了，shell那边出现broken pipe问题，但是任务基本完成，已经给出了HTML报告而且效果不错
TEST_CASES["TEST_CASE_20"] = """
针对 Agent技术 进行前沿技术研究，并生成一份包含核心论文分析及交互式HTML报告:
1. 前沿核心论文检索
搜索范围: 来源:重点关注 arXiv 以及相关领域的顶级会议或期刊(例如{会议/期刊名称})，时间范围:{时间范围}
- 筛选标准: 选取 5 篇最具技术创新性、前沿性和潜在影响力的论文。
- 信息提取 (每篇论文): 基础信息， 影响力， 核心内容 (创新点， 方法， 结果， 链接)。
2. 深度分析与可视化报告生成
- 综合分析: 技术路线， 核心模式， 潜力评估。
- 输出格式: 设计一个用于探交互式HTML报告研究数据的 交互式HTML报告 界面，部署并最终提供可访问的链接。
在报告末尾提供所有引用的核心论文和综述的链接列表。
"""

# 无法访问reddit，转向其他平台(hacker news + github)
TEST_CASES["TEST_CASE_21"] = """
使用浏览器访问https://www.reddit.com/ ，搜索 openclaw ，总结最近一周 Top 10 篇帖子，以便快速了解社区讨论的核心议题、用户反馈的关键点以及整体舆论导向。
具体要求:
1. 帖子内容概要:对于每个帖子，记录标题和URL，点击帖子标题，在网站上阅读其全部内容并进行总结，请提供一个简洁明了的概述，准确提炼其主要讨论的核心话题和论点。
2. 评论区观点分析:阅读完该帖子后，分析该帖子的评论区，总结评论的总体情绪是积极、消极还是中立，并简要说明判断依据(使用浏览器，不要使用数据分析方案)。
3. 关键讨论点提取:从评论区中识别并列出最具代表性和价值的关键讨论点或争议点。
4. 最终产物: pdf文档，包含上述内容，如果有遗漏部分在报告中提示用户。
"""

# DEFAULT_TOOLS_LIST = ["command", "write_file", "read_file", "update_progress", "call_user"]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--load_from_file", type=str, required=False)
    parser.add_argument("--query", type=str, required=False)
    parser.add_argument("--task_dir", type=str, required=False, default="default")
    parser.add_argument("--TEST_CASE", type=str, required=False, default="TEST_CASE_1")
    parser.add_argument("--dry_run", action="store_true")
    args = parser.parse_args()
    selected_test_case = TEST_CASES.get(args.TEST_CASE, TEST_CASES["TEST_CASE_1"])
    if args.dry_run:
        print("=====Dry Run Mode=====")
        os.environ["AUTOMAS_ENABLE_OBSERVE"] = "0"
    else:
        os.environ["AUTOMAS_ENABLE_OBSERVE"] = "1"
    os.environ["AUTOMAS_TASK_DIR"] = args.task_dir
    set_log_level(logging.INFO)
    print(f"TEST_CASE({args.TEST_CASE}): \n{selected_test_case}\n")
    
    @observe(
        name="main",
        span_type="main_span",
        tags={"mode": 'simple', "node_id": 6076665},  # Set static custom tag. The Priority is higher than the default tags.
        baggage={"product_id": "123456654321", "Task": args.query if args.query else selected_test_case},  # Set static custom baggage. baggage can cover tag of sample key, and will pass to child span automatically.    
    )
    def go():
        @observe(
            name="step",
            span_type="step_span",
            process_outputs=step_process_output,
            process_inputs=step_process_input,
        )
        def step(agent_factory: AgentFactory, context_manager: ContextManager, plan_agent: PlannerAgent) -> dict:
            factory_result = agent_factory.run()
            agent: Agent = factory_result["agent"]
            if not context_manager.is_executing:
                print("=====New Agent=====")
                resp_content, resp_usage, resp_status, tool_usage, qa = agent.run("执行给你的任务")
            else:
                print("=====Continue=====")
                resp_content, resp_usage, resp_status, tool_usage, qa = agent.run("")
            print("=====Agent Response===== \n", resp_content)
            print("=====Current Plan=====")
            formatted_task_plan = context_manager.get_formatted_plan(context_manager.task_state)
            print(formatted_task_plan)
            plan_result = None
            if context_manager.is_accomplished():
                is_accomplished = True
            else:
                plan_result = plan_agent.run()
                is_accomplished = plan_result["is_mission_accomplished"]
            return {
                "is_accomplished": is_accomplished,
                "formatted_task_plan": formatted_task_plan,
                "resp_content": resp_content,
                "resp_status": resp_status,
                "tool_usage": tool_usage,
            }

        @observe(
            name="loop",
            span_type="loop_span",
            process_outputs=loop_process_output,
        )
        def loop(
            is_accomplished: bool,
            agent_factory: AgentFactory,
            context_manager: ContextManager,
            plan_agent: PlannerAgent,
            summarizer_agent: SummarizerAgent,
        ) -> dict:
            while not is_accomplished:
                result = step(agent_factory, context_manager, plan_agent)
                is_accomplished = result["is_accomplished"]
                formatted_task_plan = result["formatted_task_plan"]
                resp_content = result["resp_content"]
                resp_status = result["resp_status"]

            print("All tasks accomplished.")
            print("=====Overview=====")
            task_plan = context_manager.task_state
            formatted_task_plan = context_manager.get_formatted_plan(task_plan)
            print(formatted_task_plan)
            print("=====Result=====")
            summary, summary_usage = summarizer_agent.run()
            print(summary)
            context_manager.dump()
            return {
                "summary": summary,
                "summary_usage": summary_usage,
                "task_plan": task_plan,
                "formatted_task_plan": formatted_task_plan
            }

        if os.getenv("IS_DEBUG_ENABLED", "1") == "1":
            print("=====Debug Mode Enabled=====")
            AUTO_DUMP = os.getenv("IS_DEBUG_ENABLED", "1") == "1"
            shell = PersistentShell()
            tool_executer = ToolExecuter()
            context_manager = ContextManager()
            if args.load_from_file:
                context_manager.load(args.load_from_file)
            context_manager.set_task_dir(args.task_dir)
            if AUTO_DUMP:
                context_manager.enable_auto_dump()
            notifier = Notifier(context_manager)
            DEFAULT_TOOLS_LIST = tool_executer.list_tools()
            print(f"Available tools: {DEFAULT_TOOLS_LIST}")
            # for test only
            # context_manager.add_available_resources({"公司信息，包含周报公司名称、汇报时间周期及核心内容模块": ResourceReference(description="公司信息，包含周报公司名称、汇报时间周期及核心内容模块", URI="https://www.my_company.com/report", type="from_memorybase")})
            # context_manager.add_available_resources({"需要解决的题目截图": ResourceReference(description="需要解决的题目截图", URI="image.png", type="from_memorybase")})

            claim_agent = ClaimerAgent(notifier, context_manager)
            plan_agent = PlannerAgent(context_manager, notifier, tool_executer, ["call_user", "read_file", "command"])
            summarizer_agent = SummarizerAgent(notifier, context_manager)
            agent_factory = AgentFactory(context_manager,DEFAULT_TOOLS_LIST, tool_executer, shell)
            if not context_manager.is_clarified:
                claim_agent.run(args.query if args.query else selected_test_case)
            if not context_manager.is_planned:
                plan_result = plan_agent.run()
                is_accomplished = plan_result["is_mission_accomplished"]
            else:
                is_accomplished = context_manager.is_accomplished()

            result = loop(
                is_accomplished=is_accomplished,
                agent_factory=agent_factory,
                context_manager=context_manager,
                plan_agent=plan_agent,
                summarizer_agent=summarizer_agent
            )
        else:
            shell = PersistentShell()
            tool_executer = ToolExecuter()
            context_manager = ContextManager()
            context_manager.set_task_dir(args.task_dir)
            notifier = Notifier(context_manager)
            DEFAULT_TOOLS_LIST = tool_executer.list_tools()
            print(f"Available tools: {DEFAULT_TOOLS_LIST}")
            # for test only
            # context_manager.add_available_resources({"公司信息，包含周报公司名称、汇报时间周期及核心内容模块": ResourceReference(description="公司信息，包含周报公司名称、汇报时间周期及核心内容模块", URI="https://www.my_company.com/report", type="from_memorybase")})
            # context_manager.add_available_resources({"需要解决的题目截图": ResourceReference(description="需要解决的题目截图", URI="image.png", type="from_memorybase")})

            claim_agent = ClaimerAgent(notifier, context_manager)
            plan_agent = PlannerAgent(context_manager, notifier, tool_executer, ["call_user", "read_file", "command"])
            summarizer_agent = SummarizerAgent(notifier, context_manager)
            agent_factory = AgentFactory(context_manager,DEFAULT_TOOLS_LIST, tool_executer, shell)
            claim_agent.run(args.query if args.query else selected_test_case)
            plan_result = plan_agent.run()
            is_accomplished = plan_result["is_mission_accomplished"]
            result = loop(
                is_accomplished=is_accomplished,
                agent_factory=agent_factory,
                context_manager=context_manager,
                plan_agent=plan_agent,
                summarizer_agent=summarizer_agent
            )
            
    go()

if __name__ == "__main__":
    main()
    if os.environ.get("AUTOMAS_ENABLE_OBSERVE", "0") == "1":
        flush()
    
