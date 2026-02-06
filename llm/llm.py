from .json_schemas import FactoryOutput
from volcenginesdkarkruntime import Ark
import os
from pydantic import BaseModel
from .json_schemas import ClaimerSchema, PlannedTasks
api_key = os.environ.get("ARK_API_KEY")
model = os.environ.get("MODEL")

client = Ark(   
    base_url="https://ark.cn-beijing.volces.com/api/v3",
    api_key=api_key, 
)


registered_schema = {}

registered_schema["Claimer"] = ClaimerSchema
registered_schema["Planner"] = PlannedTasks
registered_schema["PromptEngineer"] = FactoryOutput


def llm_call(messages: list, tools: list):
    """
    调用模型，返回模型的回复
    """
    resp = client.chat.completions.create(
        # 指定您创建的方舟推理接入点 ID，此处已帮您修改为您的推理接入点 ID
        model=model,
        stream=False,
        extra_body={
            "thinking": {
                "type": "disabled"
            }
        },
        messages=messages,
        tools=tools,
    )
    return resp.choices[0].finish_reason, resp.choices[0].message

# Json schema输出不可用stream参数
def llm_call_json_schema(messages: list, tools: list, jsonSchema: str):
    """
    调用模型，返回模型的回复
    """
    resp = client.beta.chat.completions.parse(
        # 指定您创建的方舟推理接入点 ID，此处已帮您修改为您的推理接入点 ID
        model=model,
        # stream=False, 
        extra_body={
            "thinking": {
                "type": "disabled"
            }
        },
        messages=messages,
        tools=tools,
        response_format=registered_schema[jsonSchema]
    )
    return resp.choices[0].finish_reason, resp.choices[0].message.parsed