from resources.tools.persistent_shell import PersistentShell
from resources.tools.skill_tool import get_skill_list
import json
from resources.tools.tool_executer import ToolExecuter
from llm.llm import llm_call, llm_call_json_schema
from llm.json_schemas import ProacvtiveQuery, ClaimerSchema
from .prompt import render
from resources.tools.notifier import Notifier

def access_knowledgeDB():
    return "None"

DEFAULT_INSTRUCTION = """
# Role
You are an expert who assesses whether existing resources can meet user needs. 
For the following cases, you dont need to be strict about the availability of resources
If the user mentions alternative ways to access resources (e.g., stating that documents or images are in a certain path), you can assume these access methods are valid except for obvious errors—you do not need to point out that you cannot access them or require text descriptions.
If the user mentions that resources is accessible, then assume that he/she is right, and there is no need to do futher query about this.
The following is a suggested assessment process: 
1. Clearly define the user's core needs.
2. Review the coverage and key information of existing resources. 
3. Compare the needs with the resources to determine if the resources adequately address the core requirements. If there are key needs not covered by the resources or insufficient information to support a solution, the resource is deemed insufficient, and then the user needs to be promptly alerted.

# Output
JSON format
"""

class ClaimerAgent:
    def __init__(self, notifier: Notifier):
        self.messages = []
        # prompt = DEFAULT_INSTRUCTION.format(access_knowledgeDB())
        prompt = DEFAULT_INSTRUCTION
        print(f"agent system prompt: {prompt}")
        self.messages.append({"role": "system", "content": prompt})
        self.notifier = notifier

    def run(self, query: str):
        print(f'ClaimerAgent Started')
        self.messages.append({"role": "user", "content": query})
        finish_reason, resp = llm_call_json_schema(self.messages, [], "Claimer")
        print(f'Finish Reason: {finish_reason}')
        # resp = resp.model_dump_json(indent=2)
        # process json output
        while resp.need_more_info:
            i = 0
            for model_query in resp.contents:
                i += 1
                model_query = model_query.query
                print(f'Model query: {model_query} | ({i} / {len(resp.contents)})')
                user_resp = self.notifier.call_user(model_query)
                self.messages.append({"role": "assistant", "content": model_query})
                self.messages.append({"role": "user", "content": user_resp})
            # self.messages.append({"role": "user", "content": "你还有想要我补充的吗，没有的话就下一步吧。"})
            finish_reason, resp = llm_call_json_schema(self.messages, [], "Claimer")
        print(f'ClaimerAgent Finished')
        return self.messages[0], self.messages[1:]
        
        