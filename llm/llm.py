from miscellaneous.cozeloop_preprocess import format_token_usage
from miscellaneous.cozeloop_preprocess import llm_call_json_schema_process_output
from miscellaneous.cozeloop_preprocess import llm_call_process_output, llm_call_process_input
from miscellaneous.cozeloop_preprocess import llm_call_json_schema_process_input
from .json_schemas import SubmitMessage
from .json_schemas import FactoryOutput
from volcenginesdkarkruntime import Ark
import os
from pydantic import BaseModel
from .json_schemas import ClaimerSchema, PlannedTasks
from miscellaneous.observe import observe
from cozeloop import flush, get_span_from_context
from control.context_manager import ContextManager
from config.logger import setup_logger

logger = setup_logger("LLM")

context_manager = ContextManager()
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
registered_schema["Submit"] = SubmitMessage

@observe(
    name="llm_call",
    span_type="model",
    tags={"mode": 'simple', "node_id": 6076665},
    process_outputs=llm_call_process_output,
    process_inputs=llm_call_process_input,
)
def llm_call(*, messages: list, tools: list):
    """
    调用模型，返回模型的回复
    """
    # print(f"llm_call messages: \n {messages}")
    # print(f"llm_call tools: \n {tools}")
    
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
        max_tokens=12 * 1024,
    )
    formatted_usage = format_token_usage(resp.usage)
    if os.environ.get("AUTOMAS_ENABLE_OBSERVE") == "1":
        get_span_from_context().set_tags({
            "input_tokens": formatted_usage["prompt_tokens"], 
            "output_tokens": formatted_usage["completion_tokens"] + formatted_usage["reasoning_token"],
            "last_dump_filepath": context_manager.last_dump_filepath
            }
        )
        flush()
    finish_reason = resp.choices[0].finish_reason
    if finish_reason == "content_filter":
        logger.warning("WARNING: 生成内容被审核拦截")
        print("WARNING: 生成内容被审核拦截")
    if finish_reason == "length":
        logger.warning("WARNING: 模型生成内容被截断")
        print("WARNING: 模型生成内容被截断")
    return finish_reason, resp.choices[0].message, resp.usage

# Json schema输出不可用stream参数
@observe(
    name="llm_call_json_schema",
    span_type="model",
     tags={"mode": 'simple', "node_id": 6076665},
    process_outputs=llm_call_json_schema_process_output,
    process_inputs=llm_call_json_schema_process_input,
)
def llm_call_json_schema(*, messages: list, tools: list, jsonSchema: str):
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
        response_format=registered_schema[jsonSchema],
        max_tokens=20 * 1024,
    )
    formatted_usage = format_token_usage(resp.usage)  
    if os.environ.get("AUTOMAS_ENABLE_OBSERVE", "0") == "1":
        get_span_from_context().set_tags({
            "input_tokens": formatted_usage["prompt_tokens"], 
            "output_tokens": formatted_usage["completion_tokens"] + formatted_usage["reasoning_token"],
            "last_dump_filepath": context_manager.last_dump_filepath
            }
        )
        flush()
    finish_reason = resp.choices[0].finish_reason
    if finish_reason == "content_filter":
        logger.warning("WARNING: 生成内容被审核拦截")
        print("WARNING: 生成内容被审核拦截")
    if finish_reason == "length":
        logger.warning("WARNING: 模型生成内容被截断")
        print("WARNING: 模型生成内容被截断")
    return finish_reason, resp.choices[0].message, resp.usage

