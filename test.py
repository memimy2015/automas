from llm.llm import llm_call_json_schema
from resources.tools.console_input import get_input
from resources.tools.skill_tool import get_skill_list
from cozeloop import flush, get_span_from_context
from miscellaneous.observe import observe
import argparse


msg = """
\n# Role\nYou are an expert in user requirement assessment, skilled at evaluating whether the requirement currently proposed by the user is a complete and executable one.\n\n# Target\nThe goal is to obtain an executable and plannable requirement through dialogue with the user. However, there is no need to pursue perfection excessively or get stuck in constant questioning.\n\n# Specific Requirements\n- The requirement must be clear and executable.\n- You are only responsible for clarifying requirements with the user. As for whether the information or documents provided by the user are true or usable, you do not need to make judgments.\n- For vague questions, if the user supplements with documents or links, the requirement shall be directly deemed sufficiently clear.\n- When the current requirement is clear, you must give an refined objective in order to guide the planner.\n- When user provides link or file path that can refer to the information, you must add it to the json output, make sure it is a valid url or file path.\n- You must add the source reference to the json output in the form of a list of ResourceReference objects, URI to the source of must be a valid url or file path.\n- Each ResourceReference object must have a description and a URI to the source of the information. The URI should be a valid url or file path.\n- If the user provides multiple links or file paths, you must add them to the json output in the form of a list of ResourceReference objects.\n- The type of each ResourceReference object must be 'from_user'.\n\n# project directory\n- project directory path(PROJECT_DIR): /mnt/c/Users/Admin/Desktop/20260203/AIME/automas\n\n\n# Output\nJSON format\n"
"""

messages = [{"role": "system", "content": msg},{"role": "user", "content": "https://www.bilibili.com/read/cv9314580/?opus_fallback=1 总结一下网页的文字内容，然后给我展示一下M1的特性和性能，包括一些参数，输出为pdf文件，美观一点"}]
tools = [
    {
        "type": "function",
        "function": {
            "name": "call_user",
            "strict": True,
            "description": "调用用户交互的工具，用于向用户获取更多信息。当你认为目前的情况需要得到用户的许可或者指挥，就使用这个方法。比如遇到权限问题时、需要用户确认某个关键操作时，又或者是遇到严重错误等，可能需要用户进行后续计划的判断的情况，此时一定要请求用户的回答。其他情况下尽量不要使用这个工具打扰用户，尤其是问候类的语句。",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "发送给用户的信息，用户需要根据这个信息进行确认或操作。如果这个信息需要用户做出选择，你最好提供几个选择给用户参考。尤其是遇到严重错误无法完成任务时，必须请求用户确认是否继续执行后续操作或者提供信息来解决错误，为此请在发给用户的提问中包含必要的信息，例如确认操作、拒绝操作、提供额外信息、解决建议等。"
                    }
                },
                "required": ["query"]
            }
        }
    }
]


print(get_skill_list())
txt = "\u001b[0m: []\nINFO     [Agent] \n📄 \u001b[32m Final Result:\u001b[0m \n已成功获取Reddit平台最近一周关于OpenCLaw的帖子信息，具体内容如下：\n1. 标题：Top Models used with OpenClaw?，发布时间：6天前，点赞数：9，评论数：15\n2. 标题：how I run a 24/7 AI company with OpenClaw for $50/month，发布时间：7天前，点赞数：139，评论数：49\n3. 标题：\"NVIDIA is now releasing their own open claw 🤯 nemoclaw will be an opensource ai agent built for the enterprise world. It can run on amd, intel, or whatever hardware NOT just nvdia gpus. \" - I am hearing claw in many places and it may well be good for Open Source!，发布时间：4天前，点赞数：11，评论数：8\n4. 标题：Making Money With Openclaw!，发布时间：7天前，点赞数：47，评论数：78\n5. 标题：Finall"
pattern = "\x1b[32m Final Result:\x1b[0m"
print(txt.split(pattern)[-1]) # 这个是应该保留的输出
parser = argparse.ArgumentParser()
parser.add_argument("--test_case", type=str, default="114514", required=False)

args = parser.parse_args()
test_case = args.test_case
print(f"test_case: \n{test_case}\n")

jsonSchema = "Planner"
finish_reason, resp, usage = llm_call_json_schema(messages=messages, tools=[], jsonSchema=jsonSchema)
print(f"finish_reason: {finish_reason}")
print(f"resp: {resp}")
print(f"resp parsed: {resp.parsed} \n {type(resp.parsed)}")
print(f"resp.content: {resp.tool_calls[0].function.name}")
print(f"resp.tool_usage: {resp.tool_calls[0].function.parsed_arguments}")
print(f"usage: {usage.model_dump()}")
