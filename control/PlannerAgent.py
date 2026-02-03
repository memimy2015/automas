from resources.tools.persistent_shell import PersistentShell
from resources.tools.skill_tool import get_skill_list
import json
from resources.tools.tool_executer import ToolExecuter
from llm.llm import llm_call, llm_call_json_schema
from execution.agent.prompt import render
from .progress_manager import ProgressManager
from typing import Optional
from llm.json_schemas import Subtask, SubtaskSteps, PlannedTasks

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

You will serve for following usages:
- Given a user query, do planning for it and then creates a hierarchical task list and next step to do.
- Given a execution result from agent, update the status of task list and do some adjustment if needed, then dispatch next step to agent.

# History
{}

# Task list example

- [x] **Objective 1: Perform Initial Research**
  - [x] Sub-objective 1.1: Research top attractions
  - [x] Sub-objective 1.2: Investigate transportation options
- [ ] **Objective 2: Finalize Itinerary and Budget**
  - [ ] Sub-objective 2.1: Research hotel accommodations
  - [ ] Sub-objective 2.2: Calculate total estimated budget
  - [ ] Sub-objective 2.3: Create final itinerary document
 
x in brackets means this objective or sub-objective is accomplished
empty brackets means this objective or sub-objective needs to be done

# Task list
Task list is in json format
If current task list is empty, you need to perform planning for global objective given by user.
If current task list already has items, you need to check history list and give an updated task list according to previous accomplishments if changes is necessary, and then decide what to do next.
If there is no need to update task list, you just need to repeat it and decide next steps to do.
When deciding next executable step, you must attach specification and details to it so as to let downstream executor works better.
current task list:
{}

# Overall goal
Goal will be given by user.

# Output format
JSON format

"""

class PlannerAgent:
    def __init__(self, progress_manager: ProgressManager):
        self.messages = []
        self.progress_manager = progress_manager
        self.history = []
        self.goal = None
        prompt = DEFAULT_INSTRUCTION.format(self.history, progress_manager.formulate_progress())
        print(f"agent system prompt: {prompt}")
        # self.messages.append({"role": "system", "content": prompt})

    def run(self, query: str, prev_msg_list: Optional[list] = None):
        """
        执行
        Args:
            query (str): 给planner的输入
            prev_msg_list (Optional[list], optional):  Defaults to None. 
            只用于从Claimer模块获取任务澄清阶段的说明
        """
        print("PlannerAgent Started")
        # Get updated task status
        updated_prompt = DEFAULT_INSTRUCTION.format(self.history, self.progress_manager.formulate_progress())
        if prev_msg_list:
            self.messages = prev_msg_list
            self.messages = [{"role": "system", "content": updated_prompt}] + self.messages
        else:
            self.messages[0] = {"role": "system", "content": updated_prompt}
            self.messages.append({"role": "user", "content": query})
        
        # Planning
        finish_reason, resp = llm_call_json_schema(self.messages, [], "Planner")
        print(resp.model_dump_json(indent=2))
        print("PlannerAgent Finished")
        return self.messages[0], self.messages[1:]
        
    def update_overall_goal(self, new_goal: str):
        old = self.goal
        self.goal = new_goal
        print(f"====GOAL CHANGED====")
        print(f"{old} -> {new_goal}")
        
    def update_history(self, new_history: str):
        print(f"New history updated: {new_history}")
        self.history.append(new_history)