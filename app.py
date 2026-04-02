import os
from prompt_manager import get_prompt_manager


PROMPT_VERSION_OVERRIDES = {
    "execution_agent.system_template": None,
    "execution_agent.submit_prompt": None,
    "agent_factory.system": None,
    "Clarifier.system": None,
    "summarizer.system": None,
    "planner.system_latest_instruction": None,
    "planner.schedule_init": None,
    "planner.schedule_continue": None,
    "planner.schedule_replan": None,
    "planner.schedule_pending": None,
}


def _apply_prompt_versions() -> None:
    pm = get_prompt_manager()
    for prompt_name, version in PROMPT_VERSION_OVERRIDES.items():
        if version:
            pm.set_active_version(prompt_name, version)


_apply_prompt_versions()

from control.SummarizerAgent import SummarizerAgent
from execution.factory.agent_factory import AgentFactory
from llm.json_schemas import ResourceReference
from control.context_manager import ContextManager
from execution.agent.agent import Agent
from control.ClarifierAgent import ClarifierAgent
from control.PlannerAgent import PlannerAgent
from resources.tools.tool_executer import ToolExecuter
from resources.tools.persistent_shell import PersistentShell
from resources.tools.file_operation import write_file, read_file
from control.notifier import Notifier
from resources.tools.console_input import get_input
import argparse
# from cozeloop import new_client, flush, get_span_from_context
from miscellaneous.observe import get_trace_id, observe, get_span_from_context
# from cozeloop.logger import set_log_level
import logging
import json
from miscellaneous.cozeloop_preprocess import loop_process_output, step_process_output, step_process_input
import traceback

# 网页模式相关导入
from api.state_pusher import StatePusher
from api.websocket_manager import WebSocketManager

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
搜索范围: 来源:重点关注 arXiv 以及相关领域的顶级会议或期刊(例如{会议/期刊名称})，时间范围: 2025年至今
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

# 提前主动判断结束了，cozeloop上报错是因为其他原因，跟任务无关
TEST_CASES["TEST_CASE_22"] = """
这是一份电商用户消费数据集，请你对这份数据进行完整的数据分析。请从用户画像、消费能力、品类偏好、复购情况、城市等级差异这几个维度进行分析，并给出结论和业务建议。
数据集：/mnt/c/Users/Admin/Desktop/20260203/AIME/automas/testcase_resources/数据分析(case22)/电商用户消费数据集.csv
字段说明：/mnt/c/Users/Admin/Desktop/20260203/AIME/automas/testcase_resources/数据分析(case22)/电商用户消费数据集-字段说明.txt
"""

# 已经完成
TEST_CASES["TEST_CASE_23"] = """
阅读指定目录代码 /mnt/c/Users/Admin/Desktop/20260203/AIME/automas/testcase_resources/prd设计(case23)/automas ，描述当前代码实现的主要功能。
根据代码主要功能，编写需求设计文档，以及前端交互原型。
整个过程要先做需求分析，然后做功能设计、交互设计、html原型开发。
设计好原型后，需要利用浏览器进行测试，并且进行相应优化。
"""

TEST_CASES["TEST_CASE_24"] = """
访问 https://pinchbench.com/ 去查看现在的榜单状况，对于前十名的模型，去查看他们的运行得分记录，里面有15个维度的得分，不要看百分数，得看具体的得分/满分，在最末尾还有23个任务的得分，也有对应的标签告诉你他们对应的是哪一类的任务，这里有精确到小数点第二位的得分情况，我现在需要你对每一个模型，统计一下每一个维度的得分/满分，能使用小数点后二位的数据来计分最好，然后输出一个csv文件，告诉我哪一个模型，对应的页面链接以及15个维度的得分情况，还有总分的得分情况
"""

# DEFAULT_TOOLS_LIST = ["command", "write_file", "read_file", "update_progress", "call_user"]


def main():
    # 调试：打印环境变量
    print("=====Environment Variables=====")
    print(f"AUTOMAS_WEB_MODE: {os.environ.get('AUTOMAS_WEB_MODE', 'NOT SET')}")
    print(f"AUTOMAS_TASK_ID: {os.environ.get('AUTOMAS_TASK_ID', 'NOT SET')}")
    print(f"AUTOMAS_TASK_DIR: {os.environ.get('AUTOMAS_TASK_DIR', 'NOT SET')}")
    print(f"IS_DEBUG_ENABLED: {os.environ.get('IS_DEBUG_ENABLED', 'NOT SET')}")
    print("================================")
    
    parser = argparse.ArgumentParser()
    parser.add_argument("--load_from_file", type=str, required=False)
    parser.add_argument("--query", type=str, required=False)
    parser.add_argument("--task_dir", type=str, required=False, default="default")
    parser.add_argument("--task_id", type=str, required=False, default=None)
    parser.add_argument("--TEST_CASE", type=str, required=False, default="")
    parser.add_argument("--dry_run", action="store_true")
    parser.add_argument("--debug", action="store_true", help="开启调试模式，启用 dump 功能")
    parser.add_argument(
        "--trace_provider",
        type=str,
        required=False,
        default=os.environ.get("AUTOMAS_TRACE_PROVIDER", "promptpilot"),
        choices=["cozeloop", "promptpilot"],
    )
    args = parser.parse_args()
    os.environ["AUTOMAS_TRACE_PROVIDER"] = args.trace_provider
    selected_test_case = TEST_CASES.get(args.TEST_CASE, "")
    if args.dry_run:
        print("=====Dry Run Mode=====")
        os.environ["AUTOMAS_ENABLE_OBSERVE"] = "0"
    else:
        os.environ["AUTOMAS_ENABLE_OBSERVE"] = "1"
    # 设置调试模式
    if args.debug:
        os.environ["IS_DEBUG_ENABLED"] = "1"
        print("=====Debug Mode Enabled=====")
    else:
        os.environ["IS_DEBUG_ENABLED"] = "0"
    os.environ["AUTOMAS_TASK_DIR"] = args.task_dir
    # set_log_level(logging.INFO)
    if selected_test_case:
        print(f"TEST_CASE({args.TEST_CASE}): \n{selected_test_case}\n")
    elif args.query:
        print(f"Query: {args.query}")
    else:
        print("No task specified. You must provide a TEST_CASE or a query.")
        exit(1)
    
    @observe(
        name="main",
        span_type="main_span",
        tags={"mode": 'simple', "node_id": 6076665, "task": args.query if args.query else selected_test_case},  # Set static custom tag. The Priority is higher than the default tags.
        baggage={"product_id": "123456654321", "Task": args.query if args.query else selected_test_case},  # Set static custom baggage. baggage can cover tag of sample key, and will pass to child span automatically.    
    )
    def go():
        span = get_span_from_context()
        if span is not None:
            trace_id = get_trace_id()
            if trace_id:
                span.set_attribute("metadata.trace_id", trace_id)
            pm = get_prompt_manager()
            prompts = pm.list_prompts()
            snapshot = {}
            for prompt_name, meta in prompts.items():
                active = meta.get("active_version")
                if active is not None:
                    span.set_attribute(f"metadata.prompt.active.{prompt_name}", active)
                versions = meta.get("versions", {})
                span.set_attribute(f"metadata.prompt.versions_count.{prompt_name}", len(versions))
                snapshot[prompt_name] = {"active": active, "versions": len(versions)}
            span.set_attribute("metadata.prompt.snapshot_json", json.dumps(snapshot, ensure_ascii=False))
            print("=====Prompt Snapshot=====")
            print(snapshot)
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

        # 全局 state_pusher 变量（用于在 loop 中访问）
        state_pusher = None
        
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
            nonlocal state_pusher  # 声明使用外部变量
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
            # 网页模式下推送最终完成状态
            if os.environ.get("AUTOMAS_WEB_MODE") == "1" and state_pusher:
                state_pusher.push("task_completed")
            return {
                "summary": summary,
                "summary_usage": summary_usage,
                "task_plan": task_plan,
                "formatted_task_plan": formatted_task_plan
            }
        try:
            if os.getenv("IS_DEBUG_ENABLED", "1") == "1":
                print("=====Debug Mode Enabled=====")
                AUTO_DUMP = os.getenv("IS_DEBUG_ENABLED", "1") == "1"
                shell = PersistentShell()
                tool_executer = ToolExecuter()
                context_manager = ContextManager()
                # 如果传入了 task_id，则设置到 context_manager
                if args.task_id:
                    context_manager.set_task_id(args.task_id)
                if args.load_from_file:
                    context_manager.load(args.load_from_file)
                context_manager.set_task_dir(args.task_dir)
                if AUTO_DUMP:
                    context_manager.enable_auto_dump()

                # 网页模式下初始化 StatePusher
                if os.environ.get("AUTOMAS_WEB_MODE") == "1":
                    task_id = os.environ.get("AUTOMAS_TASK_ID", context_manager.task_id)
                    state_pusher = StatePusher(context_manager, task_id)
                    context_manager.set_state_pusher(state_pusher)
                    # 推送初始状态
                    state_pusher.push("task_started")

                notifier = Notifier(context_manager)
                DEFAULT_TOOLS_LIST = tool_executer.list_tools()
                print(f"Available tools: {DEFAULT_TOOLS_LIST}")

                claim_agent = ClarifierAgent(notifier, context_manager)
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
                
                # 网页模式下初始化 StatePusher（非 debug 模式也需要）
                if os.environ.get("AUTOMAS_WEB_MODE") == "1":
                    task_id = os.environ.get("AUTOMAS_TASK_ID", context_manager.task_id)
                    state_pusher = StatePusher(context_manager, task_id)
                    context_manager.set_state_pusher(state_pusher)
                    # 推送初始状态
                    state_pusher.push("task_started")
                
                notifier = Notifier(context_manager)
                DEFAULT_TOOLS_LIST = tool_executer.list_tools()
                print(f"Available tools: {DEFAULT_TOOLS_LIST}")

                claim_agent = ClarifierAgent(notifier, context_manager)
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
        finally:
            pass
            if os.environ.get("AUTOMAS_ENABLE_OBSERVE", "0") == "1":
                trace_id = get_trace_id()
                if not trace_id:
                    return
                print(f"Trace ID: {trace_id}")
                dir_path = os.path.join(os.path.join(context_manager.project_dir, "traces"), context_manager.task_dir)
                os.makedirs(dir_path, exist_ok=True)
                path = os.path.join(dir_path, f"{trace_id}.txt")
                with open(path, "w") as f:
                    f.write(trace_id)
            
    go()

if __name__ == "__main__":

    try:
        main()
        # if os.environ.get("AUTOMAS_ENABLE_OBSERVE", "0") == "1":
        #     flush()
    except Exception as e:
        # if os.environ.get("AUTOMAS_ENABLE_OBSERVE", "0") == "1":
        #     flush()
        print(f"FATAL: {e}")
        traceback.print_exc()
    
    
