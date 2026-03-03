from llm.llm import llm_call_json_schema
from resources.tools.console_input import get_input
from cozeloop import flush, get_span_from_context
from miscellaneous.observe import observe
import argparse


messages = [{"role": "user", "content": "你好"},{"role": "assistant", "content": "你好！有什么我可以帮助你的吗？"},{"role": "user", "content": "我想知道你是男是女"}]
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
