import argparse
import json
import os
import sys
import traceback
from datetime import datetime
from pathlib import Path
from pydantic import BaseModel
from typing import Any

def _project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _ensure_sys_path() -> None:
    root = str(_project_root())
    if root not in sys.path:
        sys.path.insert(0, root)

def _cli_input(prompt: str) -> str:
    from resources.tools.console_input import get_input

    return get_input(prompt).strip()


def _runs_dir() -> Path:
    return _project_root() / "tmp_evaluate" / "runs"


def _run_id() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")

def _parse_csv(s: str) -> list[str]:
    if not s:
        return []
    return [x.strip() for x in s.split(",") if x.strip()]

def _to_serializable(value: Any) -> Any:
    if isinstance(value, BaseModel):
        try:
            return value.model_dump()
        except Exception:
            try:
                return value.dict()
            except Exception:
                return str(value)
    if isinstance(value, dict):
        return {str(k): _to_serializable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_to_serializable(v) for v in value]
    return value


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
""",
}

TEST_CASES["TEST_CASE_12"] = """
总结我的工作内容，生成一份工作报告pdf
报告模版及要求参考: /mnt/c/Users/Admin/Desktop/20260203/AIME/automas/testcase_resources/工作总结/个人周期报告/个人周期报告模版.pdf 
工作内容相关信息补充:
本地文件: /mnt/c/Users/Admin/Desktop/20260203/AIME/automas/testcase_resources/工作总结/个人周期报告
所有需要的信息都存放在这个文件夹下
"""

TEST_CASES["TEST_CASE_13"] = """
总结工作内容，生成一份工作报告pdf
报告模版及要求参考: /mnt/c/Users/Admin/Desktop/20260203/AIME/automas/testcase_resources/工作总结/研发团队周期报告/研发团队周期报告模版.pdf 
工作内容相关信息补充:
本地文件: /mnt/c/Users/Admin/Desktop/20260203/AIME/automas/testcase_resources/工作总结/研发团队周期报告
所有需要的信息都存放在这个文件夹下
目前是Q3季度，关于Q4的内容都是规划
"""

TEST_CASES["TEST_CASE_14"] = """
总结工作内容，生成一份工作报告pdf
报告模版及要求参考: /mnt/c/Users/Admin/Desktop/20260203/AIME/automas/testcase_resources/工作总结/项目方向报告/项目方向报告模板V2.pdf
工作内容相关信息补充:
本地文件: /mnt/c/Users/Admin/Desktop/20260203/AIME/automas/testcase_resources/工作总结/项目方向报告
所有需要的信息都存放在这个文件夹下
"""

TEST_CASES["TEST_CASE_15"] = """
阅读论文: /mnt/c/Users/Admin/Desktop/20260203/AIME/automas/essay/Agentic-Memory_Learning-Unified-Long-Term-and-Short-Term-Memory-Management-for-LLM-Agents.pdf
并且查找阅读相关和相似论文，对比不同方法的优劣，总结为一篇PDF报告
"""

TEST_CASES["TEST_CASE_16"] = """
针对智能安防与大模型技术的结合，做一些技术和市场调研，生成PPT报告
"""

TEST_CASES["TEST_CASE_17"] = """
我想要从杭州出发到西安旅游，5月1日出发，5月4日返程。人均消费1万元左右。帮我做一下行程规划。要包含交通、餐饮、住宿、景点，行程要足够细致，要按照半天为单位安排景点，要考虑景点和景点、景点和餐饮、景点和住宿之间的交通方式和距离。可以参考一些攻略。
"""

TEST_CASES["TEST_CASE_18"] = """
阅读huggingface和modelscope里面关于大模型领域的热门论文，对论文进行解读，并且对里面的核心理念给出通俗易懂的解释，写入pdf文档。
前往 https://huggingface.co/papers ，切换到 Weekly 榜单，依次浏览排名前 10 的论文。对于每篇论文:
1. 总结论文摘要，记录标题和 URL。
2. 突出显示与 强化学习 相关的论文。
3. 最后将所有内容汇总成一份结构化报告，并按相关性排序。
"""

TEST_CASES["TEST_CASE_19"] = """
帮我写个小说，12章以内，下面是题材要求：
都市轻喜剧，主打“反套路合租”，聚焦性格反差极大的三个年轻人，在一间老小区的两居室里发生的一系列搞笑又温暖的日常。社恐慢热、爱钻牛角尖的会计林晚，被迫和两个“显眼包”室友合租——话痨爱折腾、干啥啥不行的创业未遂者江熠，以及看似高冷毒舌、实则爱管闲事的宠物医院助理苏冉。三人性格碰撞不断，从最初的互相嫌弃、鸡飞狗跳，到后来的彼此包容、互相搭救，没有狗血剧情，全是接地气的搞笑日常、细碎的温暖瞬间，主打轻松解压，贴合当代年轻人的合租生活，既有笑点又有共鸣，适合碎片化阅读和长期连载。
"""

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

TEST_CASES["TEST_CASE_21"] = """
使用浏览器访问https://www.reddit.com/ ，搜索 openclaw ，总结最近一周 Top 10 篇帖子，以便快速了解社区讨论的核心议题、用户反馈的关键点以及整体舆论导向。
具体要求:
1. 帖子内容概要:对于每个帖子，记录标题和URL，点击帖子标题，在网站上阅读其全部内容并进行总结，请提供一个简洁明了的概述，准确提炼其主要讨论的核心话题和论点。
2. 评论区观点分析:阅读完该帖子后，分析该帖子的评论区，总结评论的总体情绪是积极、消极还是中立，并简要说明判断依据(使用浏览器，不要使用数据分析方案)。
3. 关键讨论点提取:从评论区中识别并列出最具代表性和价值的关键讨论点或争议点。
4. 最终产物: pdf文档，包含上述内容，如果有遗漏部分在报告中提示用户。
"""

TEST_CASES["TEST_CASE_22"] = """
这是一份电商用户消费数据集，请你对这份数据进行完整的数据分析。请从用户画像、消费能力、品类偏好、复购情况、城市等级差异这几个维度进行分析，并给出结论和业务建议。
数据集：/mnt/c/Users/Admin/Desktop/20260203/AIME/automas/testcase_resources/数据分析(case22)/电商用户消费数据集.csv
字段说明：/mnt/c/Users/Admin/Desktop/20260203/AIME/automas/testcase_resources/数据分析(case22)/电商用户消费数据集-字段说明.txt
"""

TEST_CASES["TEST_CASE_23"] = """
阅读指定目录代码 /mnt/c/Users/Admin/Desktop/20260203/AIME/automas/testcase_resources/prd设计(case23)/automas ，描述当前代码实现的主要功能。
根据代码主要功能，编写需求设计文档，以及前端交互原型。
整个过程要先做需求分析，然后做功能设计、交互设计、html原型开发。
设计好原型后，需要利用浏览器进行测试，并且进行相应优化。
"""

TEST_CASES["TEST_CASE_24"] = """
访问 https://pinchbench.com/ 去查看现在的榜单状况，对于前十名的模型，去查看他们的运行得分记录，里面有15个维度的得分，不要看百分数，得看具体的得分/满分，在最末尾还有23个任务的得分，也有对应的标签告诉你他们对应的是哪一类的任务，这里有精确到小数点第二位的得分情况，我现在需要你对每一个模型，统计一下每一个维度的得分/满分，能使用小数点后二位的数据来计分最好，然后输出一个csv文件，告诉我哪一个模型，对应的页面链接以及15个维度的得分情况，还有总分的得分情况
"""


def _reset_singletons() -> None:
    from control.context_manager import ContextManager
    from control.notifier import Notifier

    ContextManager._instance = None
    ContextManager._initialized = False
    Notifier._instance = None
    Notifier._initialized = False


class CLIInteractiveNotifier:
    def __init__(self, max_calls: int | None):
        self.max_calls = max_calls
        self.calls: list[dict[str, str]] = []

    def call_user(self, notification_msg: str, invoker_agent_id: int, in_channel: str, out_channel="user"):
        self.calls.append({"question": str(notification_msg), "answer": ""})
        if self.max_calls is not None and len(self.calls) > self.max_calls:
            raise RuntimeError(f"Exceeded max_user_calls={self.max_calls}")
        print("\n[Claimer Question]")
        print(notification_msg)
        ans = _cli_input("[Your Answer] ")
        self.calls[-1]["answer"] = ans
        return ans


def _print_case(case_id: str, query: str) -> None:
    print("\n=====Selected Case=====")
    print(case_id)
    print("=====Query=====")
    print(query.strip())


def _select_case(case_id: str | None) -> tuple[str, str]:
    keys = sorted(TEST_CASES.keys())
    if case_id and case_id in TEST_CASES:
        return case_id, TEST_CASES[case_id]
    print("=====Available Cases=====")
    for k in keys:
        print(k)
    picked = _cli_input("Select a case id: ")
    if picked not in TEST_CASES:
        raise ValueError(f"Unknown case id: {picked}")
    return picked, TEST_CASES[picked]


def _write_json(path: Path, obj) -> None:
    obj = _to_serializable(obj)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")

def _append_jsonl(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(_to_serializable(obj), ensure_ascii=False) + "\n")


def _prompt_versions_snapshot() -> dict[str, dict[str, object]]:
    from prompt_manager import get_prompt_manager

    pm = get_prompt_manager()
    prompts = pm.list_prompts()
    snapshot: dict[str, dict[str, object]] = {}
    for prompt_name, meta in prompts.items():
        active = meta.get("active_version")
        versions = meta.get("versions", {})
        snapshot[prompt_name] = {"active": active, "versions": len(versions) if isinstance(versions, dict) else 0}
    return snapshot


def run_one(case_id: str, query: str, task_dir: str, max_user_calls: int) -> dict:
    os.environ["AUTOMAS_TASK_DIR"] = task_dir
    os.environ["AUTOMAS_ENABLE_OBSERVE"] = os.environ.get("AUTOMAS_ENABLE_OBSERVE", "0")

    _reset_singletons()
    from control.context_manager import ContextManager
    from control.ClaimerAgent import ClaimerAgent

    context = ContextManager()
    notifier = CLIInteractiveNotifier(max_calls=max_user_calls)
    agent = ClaimerAgent(notifier=notifier, context_manager=context)

    started_at = datetime.now().isoformat(timespec="seconds")
    try:
        result = agent.run(query)
        ended_at = datetime.now().isoformat(timespec="seconds")
        return {
            "case_id": case_id,
            "task_dir": task_dir,
            "started_at": started_at,
            "ended_at": ended_at,
            "ok": True,
            "result": result,
            "qa": list(notifier.calls),
            "prompt_versions": _prompt_versions_snapshot(),
        }
    except Exception as e:
        ended_at = datetime.now().isoformat(timespec="seconds")
        return {
            "case_id": case_id,
            "task_dir": task_dir,
            "started_at": started_at,
            "ended_at": ended_at,
            "ok": False,
            "error": str(e),
            "traceback": traceback.format_exc(),
            "qa": list(notifier.calls),
            "prompt_versions": _prompt_versions_snapshot(),
        }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", type=str, default="")
    parser.add_argument("--query", type=str, default="")
    parser.add_argument("--max-user-calls", type=int, default=6)
    parser.add_argument("--task-dir", type=str, default="")
    args = parser.parse_args(argv)

    _ensure_sys_path()
    run_root = _runs_dir() / "interactive" / _run_id()
    results_jsonl = run_root / "results.jsonl"

    prompt_snapshot = _prompt_versions_snapshot()
    print("\n=====Prompt Versions=====")
    for name in sorted(prompt_snapshot.keys()):
        meta = prompt_snapshot[name]
        print(f"{name}\tactive={meta.get('active')}\tversions={meta.get('versions')}")

    selected: list[tuple[str, str]] = []
    if args.query.strip():
        selected = [("QUERY", args.query)]
    elif args.case.strip():
        picked = _parse_csv(args.case)
        for cid in picked:
            if cid not in TEST_CASES:
                raise ValueError(f"Unknown case id: {cid}")
        selected = [(cid, TEST_CASES[cid]) for cid in picked]
    else:
        selected = [(cid, TEST_CASES[cid]) for cid in sorted(TEST_CASES.keys())]

    for i, (case_id, query) in enumerate(selected, start=1):
        print("\n==============================")
        print(f"Case {i}/{len(selected)}")
        _print_case(case_id, query)
        if not args.case.strip() and not args.query.strip():
            action = _cli_input("Press Enter to run, 's' to skip, 'q' to quit: ").lower()
            if action == "q":
                break
            if action == "s":
                continue

        if args.task_dir.strip():
            task_dir = args.task_dir.strip()
        else:
            suffix = f"{case_id}_{i}" if (args.case.strip() and len(selected) > 1) else case_id
            task_dir = f"eval_{run_root.name}_{suffix}"
        row = run_one(
            case_id=case_id,
            query=query,
            task_dir=task_dir,
            max_user_calls=args.max_user_calls,
        )

        print("\n=====Claimer Result=====")
        print(json.dumps(_to_serializable(row.get("result", row)), ensure_ascii=False, indent=2))

        print("\n=====Your Feedback=====")
        rating_s = _cli_input("Rating (1-5, optional): ")
        rating = None
        if rating_s:
            try:
                rating = int(rating_s)
            except Exception:
                rating = None
        feedback_text = _cli_input("Feedback: ")
        row["feedback"] = {"rating": rating, "text": feedback_text}

        prompt_active_versions: dict[str, str] = {}
        for k, v in (row.get("prompt_versions") or {}).items():
            if isinstance(v, dict) and v.get("active"):
                prompt_active_versions[str(k)] = str(v.get("active"))

        out = {
            "case_id": case_id,
            "query": query,
            "task_dir": task_dir,
            "prompt_versions": row.get("prompt_versions", {}),
            "prompt_active_versions": prompt_active_versions,
            "feedback": row.get("feedback", {}),
            "qa": row.get("qa", []),
            "claimer": row.get("result", {}),
            "ok": row.get("ok", False),
        }
        out_path = run_root / f"{case_id}.json"
        _write_json(out_path, out)
        _append_jsonl(results_jsonl, out)
        print("\n=====Saved=====")
        print(str(out_path))

        if not args.case.strip() and not args.query.strip():
            cont = _cli_input("Continue to next case? (Enter=yes, 'q'=quit): ").lower()
            if cont == "q":
                break

    print("\n=====Run Summary=====")
    print(str(results_jsonl))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
