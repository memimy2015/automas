from miscellaneous.cozeloop_preprocess import format_token_usage
from miscellaneous.cozeloop_preprocess import llm_call_json_schema_process_output
from miscellaneous.cozeloop_preprocess import llm_call_process_output, llm_call_process_input
from miscellaneous.cozeloop_preprocess import llm_call_json_schema_process_input
from .json_schemas import SubmitMessage
from .json_schemas import FactoryOutput
from volcenginesdkarkruntime import Ark
import os
from pydantic import BaseModel, Field
from .json_schemas import ClaimerSchema, PlannedTasks, Replan, ContinueNextStep, JudgePlannerState
from miscellaneous.observe import observe
from cozeloop import flush, get_span_from_context
from control.context_manager import ContextManager
from config.logger import setup_logger
import time
import random

MAX_RETRIES = 5

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
registered_schema["Planner"] = Replan
registered_schema["PromptEngineer"] = FactoryOutput
registered_schema["Submit"] = SubmitMessage
registered_schema["JudgePlannerState"] = JudgePlannerState
registered_schema["ContinueNextStep"] = ContinueNextStep
registered_schema["Replan"] = Replan


class LLMErrorMessage(BaseModel):
    role: str = "assistant"
    content: str = ""
    tool_calls: list = Field(default_factory=list)
    parsed: object | None = None

    def model_dump(self, *args, **kwargs):
        return {"role": self.role, "content": self.content}


class LLMErrorUsage:
    def model_dump(self, *args, **kwargs):
        return {}


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, str(default)))
    except Exception:
        return default


def _retry_call(fn, *, max_retries: int):
    last_exc: Exception | None = None
    for attempt in range(max_retries + 1):
        print(f"llm attempt: {attempt}")
        try:
            return fn()
        except Exception as e:
            last_exc = e
        if attempt < max_retries:
            time.sleep(min(2 ** attempt, 8) + random.random() * 0.2)
    raise last_exc if last_exc else RuntimeError("LLM call failed")

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
    
    max_retries = _env_int("AUTOMAS_LLM_MAX_RETRIES", MAX_RETRIES)
    try:
        def _do_call():
            return client.chat.completions.create(
                model=model,
                stream=False,
                extra_body={
                    "thinking": {
                        "type": "disabled"
                    }
                },
                messages=messages,
                tools=tools,
                max_tokens=30 * 1024,
            )

        resp = _retry_call(_do_call, max_retries=max_retries)
    except Exception as e:
        logger.error(f"llm_call failed after retries: {e}")
        return "error", LLMErrorMessage(content=f"LLM调用失败：{e}"), LLMErrorUsage()
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
    max_retries = _env_int("AUTOMAS_LLM_MAX_RETRIES", MAX_RETRIES)
    try:
        def _do_call():
            return client.beta.chat.completions.parse(
                model=model,
                extra_body={
                    "thinking": {
                        "type": "disabled"
                    }
                },
                messages=messages,
                tools=tools,
                response_format=registered_schema[jsonSchema],
                max_tokens=30 * 1024,
            )

        resp = _retry_call(_do_call, max_retries=max_retries)
    except Exception as e:
        logger.error(f"llm_call_json_schema failed after retries: {e}")
        parsed_default = None
        schema = registered_schema.get(jsonSchema)
        if schema is not None:
            try:
                parsed_default = schema()
            except Exception:
                if jsonSchema == "Submit":
                    parsed_default = schema(task_name="", task_summary=f"LLM调用失败：{e}", task_status="failed")
        return "error", LLMErrorMessage(content=f"LLM调用失败：{e}", parsed=parsed_default), LLMErrorUsage()
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
