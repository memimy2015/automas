from execution.agent.prompt import PROJECT_DIR
from control.context_manager import ContextManager
from resources.tools.persistent_shell import PersistentShell
from resources.tools.skill_tool import get_skill_list
import json
from resources.tools.tool_executer import ToolExecuter
from llm.llm import llm_call, llm_call_json_schema
from execution.agent.prompt import render
from typing import Optional
from llm.json_schemas import Subtask, SubtaskSteps, PlannedTasks
from .notifier import Notifier

CN_PROMPT = """
你是一个任务规划专家，现在需要根据用户提出的具体问题，按照“问题拆解→子问题验证→流程优化”的逻辑，将问题分解为更细致、无遗漏的子问题（需覆盖问题的核心要素、关联条件及潜在边界），并为每个子问题设计顺畅且正确的解决流程：首先明确子问题的目标与输入输出要求，其次规划分步骤的执行逻辑（含关键判断节点与应对方案），最后说明子问题间的衔接关系，确保整体流程可落地、无逻辑断层。
"""
DEFAULT_INSTRUCTION = """
# Role
You are a task planning expert. 
Now you need to break down the specific problem raised by the user into more detailed and comprehensive sub-problems (covering the core elements, related conditions, and potential boundaries of the problem) according to the logic of "problem decomposition → sub-problem verification → process optimization". 
For each sub-problem, you need to design a smooth and correct solution process, the following steps is a basic strategy: 
1. clarify the goal and input/output requirements of the sub-problem
2. plan the step-by-step execution logic (including key judgment nodes and solutions)
3. explain the connection between the sub-problems to ensure that the overall process is feasible and has no logical gaps.
4. sub-objective must be clear and executable and do not have sub-objective with repeated content or obvious overlap, if there is, you can merge them into one sub-objective or let new sub-objective utilizes the existing one's content rather than creates it again.

You will serve for following usages:
- Given a user query, do planning for it and then creates a hierarchical task list and next step to do.
- Given a execution result from agent, update the task list and do some adjustment about planning if needed, then dispatch next step to agent.
- Given user chat history, current task list and overall goal, do planning for the user query, if there is no adjustment about planning, dispatch next step to agent, otherwise, set need_replan to True and give replan_reason and task_specification, then user will provide more information according to task_specification provided by you or do the judgment and this will be demonstrated in section 'Chat History', latest message will be the last one. Once you receive user messages, try to do planning again.


# Specific requirements
- SubtaskSteps object is the only object that contains executable information, therefore you must make sure objective in Subtask object is not an empty list.
- task_name field in the task list is the name of a group of sub_objectives.
- When editing next_step objective, you must be very careful to set the status of the objective_index and sub_objective_index correctly. They refer to the index of the objective and sub-objective in the task list respectively and it is 0-indexed. You can check the index in the task list to decide how to fill in these field, however, task index in following task list is 1-indexed human-readable format, you should pay attention to the difference.
- You must not edit the status or finished state or is_mission_accomplished state of the sub-objective or objective in the task list, if there is no adjustment about planning. And if you adjust the planning, you must be careful to set the finished state, is_mission_accomplished state and status correctly. Caution! status only got four choices, ["pending", "completed", "failed", "cancelled"].
- You need to attach the resource reference to the task list. 
- If there are available sources that helps to accomplish the sub-objective or objective, corresponding objective must have a description and a URI to the source of the information. The URI should be a valid url or file path. And type in ResourceReference object must be one of from_user or from_memorybase or from_agent, you will be given the type of source reference, and you should not edit this field.
- If the user provides multiple links or file paths, you must add them to the json output in the form of a list of ResourceReference objects.
- Status for each sub-objective in the task list is one of pending, completed, failed, cancelled.
- Name of objective can be a description of the objective.
- Sub-objective must be executable step rather than summary or description.
- Next step must be in the form of NextStep object.
- Next step must contain objective_index and sub_objective_index, and both must be non-negative integers and less than the number of objectives and sub-objectives respectively.
- Next step is the first sub-objective with pending status.
- Milestones must be in the form of strings, and each milestone must be a description of the milestone, you just need to read this section to catch up with current accomplishments and do not modify it.
- Overall goal must be in the form of strings, and it must be the same as overall goal in latest task, if it is not empty and there is no need to change it.
- If there is a critical problem in the task, you must update the overall goal to reflect the problem, and set need_replan to True to ask user for more information and then fill them into task_specification. You must also provide a reason for replanning in replan_reason field. Once user gives more information, you must repeat the planning process and if there is no need to re, you just need to repeat it and decide next steps to do.
- If a user requests to check files within a folder as resources for a task, it's best to treat folder checking as a separate step to prevent the folder from becoming too large to handle in a single step. If the folder is found to be too full, the task plan should be modified to distribute file reading across different tasks. Similarly, it's advisable to check other potentially resource-intensive items before making any decisions.

# Chat History
{ChatHistory}

# Task 
Task is in Markdown format.
If current task is empty, you need to perform planning for overall goal given by user.
If current task already has items, you need to check history list and give an updated task list according to previous accomplishments if changes is necessary, and then decide what to do next.
If there is no need to update task, you just need to repeat it and decide next steps to do.
When deciding next executable step, you must attach specification and details to it so as to let downstream executor works better.
latest task list:
{TaskList}

# Overall goal
Current overall goal: {OverallGoal}

# Replan schedule (if needed)

First, review all completed tasks and subtasks. 
If a completed task or subtask is not affected by the current changes, keep it unchanged in the next plan.

Then, determine the next step to execute.

In the `next_step` object:
- `objective_index` refers to the index of the objective in the task list.
- `sub_objective_index` refers to the index of the sub-objective within that objective.
- Both indices are 0-based.

# Project directory
- project directory path(PROJECT_DIR): {PROJECT_DIR}


# Output format
JSON format

"""

REPLAN_SCHEDULE = """
# Replan schedule (if needed)

First, review all completed tasks and subtasks. 
If a completed task or subtask is not affected by the current changes, keep it unchanged in the next plan.

Then, determine the next step to execute.

In the `next_step` object:
- `objective_index` refers to the index of the objective in the task list.
- `sub_objective_index` refers to the index of the sub-objective within that objective.
- Both indices are 0-based.
"""

class PlannerAgent:
    def __init__(self, context_manager: ContextManager, notifier: Notifier):
        self.messages = []
        self.context_manager = context_manager
        self.notifier = notifier
        self.goal = None
        prompt = DEFAULT_INSTRUCTION.format(
            PROJECT_DIR=context_manager.get_project_dir(),
            ChatHistory=self.context_manager.get_formatted_dialogue(), 
            OverallGoal=self.context_manager.get_overall_goal(), 
            TaskList=self.context_manager.get_formatted_plan(self.context_manager.get_task_status()[0])
        )
        self.messages.append({"role": "system", "content": prompt})
        self.messages.append({"role": "user", "content": "Now start planning the task."})



    def run(self):
        """
        执行规划任务
        Args:
            None
        """
        print("=====PlannerAgent Started=====")
        # Get updated task status
        self._prepare_context()
        
        # Planning
        finish_reason, resp = llm_call_json_schema(self.messages, [], "Planner")
        print(resp.model_dump_json(indent=2))
        self.context_manager.set_task_status(resp)
        
        while resp.need_replan:
            print(f"=====Replan Required, reason: {resp.replan_reason}=====")
            for model_query in resp.task_specification:
                user_resp = self.notifier.call_user("[Planner]" + model_query.query)
            self._prepare_context()
            finish_reason, resp = llm_call_json_schema(self.messages, [], "Planner")
            print(resp.model_dump_json(indent=2))
            self.context_manager.set_task_status(resp)
        print("=====PlannerAgent Finished=====")
        return resp.is_mission_accomplished
        
    def _prepare_context(self, need_replan: bool = False, replan_reason: str = ""):
        updated_prompt = DEFAULT_INSTRUCTION.format(
            PROJECT_DIR=self.context_manager.get_project_dir(),
            ChatHistory=self.context_manager.get_formatted_dialogue(), 
            OverallGoal=self.context_manager.get_overall_goal(), 
            TaskList=self.context_manager.get_formatted_plan(self.context_manager.get_task_status()[0])
        )
        self.messages[0] = {"role": "system", "content": updated_prompt}
        self.messages[1] = {
            "role": "user", "content": "Now start planning the task." if need_replan else
                            "Replan required, reason: " + replan_reason + "\n " + REPLAN_SCHEDULE
        }      