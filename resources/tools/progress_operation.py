from llm.json_schemas import ResourceReference
from multiprocessing import context
from control.context_manager import ContextManager
from typing import List, Dict, Any, Literal
context_manager = ContextManager()

def update_progress(info: str):
    """
    Update current task with latest crucial information

    Args:
        info (str): crucial information, such as fatal error or a critical step to success
    """
    print(f"Add milestone: {info}")
    try:
        context_manager.add_milestone(info)
        success_msg = f"Add milestone {info} successfully."
        return success_msg
    except Exception as e:
        error_msg = f"Failed to add milestone {info}. Error: {e}"
        return error_msg
    
def submit(task_name: str, task_summary: str, task_status: Literal["pending", "completed", "stopped", "cancelled"], resources: List[Dict[str, str]]):
    """
    Submit a task with the given name, summary, status, and resources.

    Args:
        task_name (str): the name of the task
        task_summary (str): a summary of the task
        task_status (Literal["pending", "completed", "stopped", "cancelled"]): the status of the task
        files (List[Dict[str, Any]]): a list of files to be submitted
    """
    print(f'Submitting task {task_name} with summary {task_summary} and status {task_status}')
    new_files = {}
    for resource in resources:
        resource["type"] = "from_agent"
        desc = resource["description"]
        new_files[desc] = ResourceReference(**resource)
    try:
        context_manager.submit_sub_objective(task_summary, task_status, new_files)
        success_msg = f"Submit task {task_name} with summary {task_summary} and status {task_status} successfully."
        return success_msg
    except Exception as e:
        error_msg = f"Failed to submit task {task_name} with summary {task_summary} and status {task_status}. Error: {e}"
        return error_msg
