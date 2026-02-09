from control.context_manager import ContextManager
from resources.tools.persistent_shell import PersistentShell
from resources.tools.skill_tool import get_skill_list
import json
from resources.tools.tool_executer import ToolExecuter
from llm.llm import llm_call, llm_call_json_schema
from llm.json_schemas import ProacvtiveQuery, ClaimerSchema
from execution.agent.prompt import render
from .notifier import Notifier

def access_knowledgeDB():
    return "None"

DEFAULT_INSTRUCTION = """
# Role
You are an expert in user requirement assessment, skilled at evaluating whether the requirement currently proposed by the user is a complete and executable one.

# Target
The goal is to obtain an executable and plannable requirement through dialogue with the user. However, there is no need to pursue perfection excessively or get stuck in constant questioning.

# Specific Requirements
- The requirement must be clear and executable.
- You are only responsible for clarifying requirements with the user. As for whether the information or documents provided by the user are true or usable, you do not need to make judgments.
- For vague questions, if the user supplements with documents or links, the requirement shall be directly deemed sufficiently clear.
- When the current requirement is clear, you must give an refined objective in order to guide the planner.
- When user provides link or file path that can refer to the information, you must add it to the json output, make sure it is a valid url or file path.
- You must add the source reference to the json output in the form of a list of ResourceReference objects, URI to the source of must be a valid url or file path.
- Each ResourceReference object must have a description and a URI to the source of the information. The URI should be a valid url or file path.
- If the user provides multiple links or file paths, you must add them to the json output in the form of a list of ResourceReference objects.
- The type of each ResourceReference object must be 'from_user'.


# Output
JSON format
"""

class ClaimerAgent:
    def __init__(self, notifier: Notifier, context_manager: ContextManager):
        self.messages = []
        # prompt = DEFAULT_INSTRUCTION.format(access_knowledgeDB())
        prompt = DEFAULT_INSTRUCTION
        self.messages.append({"role": "system", "content": prompt})
        self.notifier = notifier
        self.context_manager = context_manager

    def run(self, query: str):
        print("=====ClaimerAgent Started=====")
        if self.context_manager.get_available_resources():
            formatted_available_resources = self.context_manager.get_formatted_available_resources()
            self.messages.append({"role": "user", "content": formatted_available_resources})
        self.messages.append({"role": "user", "content": query})
        finish_reason, resp = llm_call_json_schema(self.messages, [], "Claimer")
        print(f'Finish Reason: {finish_reason}')
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
        print(f"Source reference: \n {resp.resource_reference}")
        print(f"Refined objective: \n {resp.refined_objective}")
        self.messages.append({"role": "user", "content": f"现在的目标是：{resp.refined_objective}"})
        self.context_manager.update_overall_goal(resp.refined_objective)
        for source_ref in resp.resource_reference:
            self.messages.append({"role": "user", "content": f"资源描述：{source_ref.description} | 资源URI: {source_ref.URI} | 资源来源类型(type): {source_ref.type}"})
            self.context_manager.add_available_resources({source_ref.description: source_ref})
        for msg in self.messages[1:]:
            self.context_manager.add_dialogue(msg)
        print("=====ClaimerAgent Finished=====")
        return self.messages[0], self.messages[1:]
        
        