# from control.context_manager import ContextManager
# from execution.factory.agent_factory import AgentFactory
from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from control.context_manager import ContextManager
    from execution.factory.agent_factory import AgentFactory
    
def loop_process_output(input: dict) -> dict:
    """
    Preprocess the input for the loop.
    """
    return {
            "summary": input["summary"],
            "task_plan": input["task_plan"],
            "formatted_task_plan": input["formatted_task_plan"]
        }

def step_process_output(input: dict) -> dict:
    """
    Preprocess the input for the step.
    """
    return {
            "is_accomplished": input["is_accomplished"],
            "formatted_task_plan": input["formatted_task_plan"],
            "resp_content": input["resp_content"],
            "resp_status": input["resp_status"],
            "tool_usage": input["tool_usage"],
        }

def step_process_input(input: dict) -> dict:
    """
    Preprocess the input for the step.
    """
    args = input["args"]
    kwargs = input["kwargs"]
    
    agent_factory: AgentFactory = args[0]
    context_manager: ContextManager = args[1]
    i, j = context_manager._get_current_indices()
    subtask_step = context_manager.get_subtask_step(i, j)
    return {
            "sub-objective": context_manager.get_formatted_subtask_step(subtask_step, i + 1, j + 1)
        }

def agent_factory_process_output(input: dict) -> dict:
    """
    Preprocess the input for the agent factory.
    """
    return {
            "role": input["instruction"]["role_setting"],
            "task_specification": input["instruction"]["task_specification"],
        }

def llm_call_process_output(output: tuple) -> dict:
    """
    Preprocess the input for the llm call.
    """
    response = output[1]
    response_dump = response.model_dump() if hasattr(response, "model_dump") else response
    return {
            "finish_reason": output[0],
            "response": response_dump,
            "reasoning": getattr(response, "reasoning_content", None),
            "usage": output[2].model_dump(),
        }
    
def llm_call_process_input(input: dict) -> dict:
    """
    Preprocess the input for the llm call.
    """
    args = input["args"]
    kwargs = input["kwargs"]
    if args:
        raise ValueError("llm_call 只支持关键字传参，请使用 messages=..., tools=...")
    if "messages" not in kwargs or "tools" not in kwargs:
        raise ValueError("llm_call 缺少关键字参数 messages 或 tools")
    messages = kwargs["messages"]
    if isinstance(messages, list) and len(messages) > 8:
        messages = messages[:4] + messages[-4:]
    return {
            "messages": messages,
            "tools": kwargs["tools"],
        }
    
    
def llm_call_json_schema_process_output(output: tuple) -> dict:
    """
    Preprocess the input for the llm call.
    """
    response = output[1]
    return {
            "finish_reason": output[0],
            "response": response.parsed.model_dump() if output[0] != "tool_calls" else response.tool_calls[0].function.model_dump(),
            "reasoning": getattr(response, "reasoning_content", None),
            "usage": output[2].model_dump(),
        }

def llm_call_json_schema_process_input(input: dict) -> dict:
    """
    Preprocess the input for the llm call.
    """
    args = input["args"]
    kwargs = input["kwargs"]
    if args:
        raise ValueError("llm_call_json_schema 只支持关键字传参，请使用 messages=..., tools=..., jsonSchema=...")
    if "messages" not in kwargs or "tools" not in kwargs or "jsonSchema" not in kwargs:
        raise ValueError("llm_call_json_schema 缺少关键字参数 messages、tools 或 jsonSchema")
    messages = kwargs["messages"]
    if isinstance(messages, list) and len(messages) > 8:
        messages = messages[:4] + messages[-4:]
    return {
            "messages": messages,
            "tools": kwargs["tools"],
            "jsonSchema": kwargs["jsonSchema"],
        }

def planner_process_output(input: dict) -> dict:
    """
    Preprocess the input for the planner.
    """
    return {
            "is_mission_accomplished": input["is_mission_accomplished"],
            "formatted_plan": input["formatted_plan"],
            "action": input["action"].model_dump(),
            "total_usage": input["total_usage"].model_dump(),
            "QA": input["QA"]
        }

def Clarifier_process_output(input: dict) -> dict:
    """
    Preprocess the input for the Clarifier.
    """
    return {
            "Refined_objective": input["Refined_objective"],
            # "resource_reference": [resource.model_dump() for resource in input["resource_reference"]],
            "resource_reference": [resource.model_dump() for resource in input["resource_reference"]],
            # "total_usage": input["total_usage"].model_dump(),
            "total_usage": input["total_usage"].model_dump(),
            "QA": input["QA"]
        }
    
def agent_process_output(input: tuple) -> dict:
    """
    Preprocess the input for the agent.
    """
    return {
            "result": input[0],
            "usage": input[1].model_dump(),
            "status": input[2],
            "tool_usage": input[3],
            "QA": input[4]
        }   
    
def summarizer_process_output(input: tuple) -> dict:
    """
    Preprocess the input for the summarizer.
    """
    return {
            "summary": input[0],
            "usage": input[1].model_dump(),
        }
    
def format_token_usage(usage: dict) -> dict:
    """
    Format the token usage.
    """
    if not isinstance(usage, dict):
        usage = usage.model_dump()
    return {
        "reasoning_token": usage["completion_tokens_details"]["reasoning_tokens"],
        "prompt_tokens": usage["prompt_tokens"],
        "completion_tokens": usage["completion_tokens"],
    }
    
