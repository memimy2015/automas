from miscellaneous.cozeloop_preprocess import planner_process_output
from typing import List
from datetime import datetime
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
import os
from miscellaneous.observe import observe

CURRENT_FILE_DIR = os.path.dirname(os.path.abspath(__file__))
AUTOMAS_DIR = os.path.dirname(CURRENT_FILE_DIR)  # Go up two levels: execution/agent -> execution -> automas

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
- Given a user query, do planning for it and then creates a hierarchical task list and next step to do. If current context is vague and can not give a clear plan, you can ask user for more information by calling call_user tool.
- Given a execution result from agent, update the task list and do some adjustment about planning if needed, then dispatch next step to agent.
- Given user chat history, current task list and overall goal, do planning for the user query, if there is no adjustment about planning, dispatch next step to agent, otherwise, set need_replan to True and give replan_reason and task_specification, then user will provide more information according to task_specification provided by you or do the judgment and this will be demonstrated in section 'Chat History', latest message will be the last one. Once you receive user messages, try to do planning again.

# tool use specification

## call_user

The `call_user` tool may be invoked only when the user’s objective, constraints, or expected outcome are unclear, and clarification is required to ensure the final result aligns with the user’s intent.

It must **not** be used for:

* Resolving implementation-level uncertainties (e.g., how to use skills or internal tools).
* Managing execution details that should be handled by subagents.
* Redundant clarification, such as permission to continue operations.
* Asking whether to proceed with standard operations, with or without side effects.

You should:

* Use this tool strictly as a last resort when the user’s expectations or success criteria are ambiguous.
* Focus only on clarifying the desired outcome, not the execution strategy.
* Pay attention to the aesthetics of the format; Markdown format is recommended.

# final output directory
- final output directory path: {OUTPUT_DIR}
- Determine whether the results of processing or analysis need to be generated in the form of files based on user requirements. All deliverables shall be placed in the final output directory of the current project. If this directory does not exist, create it.
- You must create a folder in the final output directory to store the deliverables, named what you think is appropriate.
- You must not create or delete any file other than final output folder and tmp folder.

# tmp directory
- tmp directory path: {TMP_DIR}
- All temporary files generated during the process are stored in the tmp directory, do not delete temporary files.

# Project directory
- project directory path(PROJECT_DIR): {PROJECT_DIR}
- You **must not** create any file or folder in the project directory, put them to final output or tmp directory.

# note
When reading and writing files, attention should be paid to the issue of **Chinese character encoding**. Do not display garbled Chinese characters.
For example, register Arial Unicode MS for Chinese support or use command line to execute `fc-list :lang=zh | head -5` to check the available Chinese fonts and use these font when generating pdf.

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

# Output format
JSON format
"""

OPTIMIZED_INSTRUCTION = """
# Role

You are an Enterprise-Level Planning Controller in a multi-agent orchestration system.
Your responsibility is NOT task execution, but structured coordination and strategic control.
You must:

- Decompose the overall goal into coherent sub-objectives suitable for independent agent delegation.
- Ensure each sub-objective represents a meaningful and self-contained workload.
- Maintain logical integrity of the task graph.
- Continuously evaluate structural efficiency and detect optimization opportunities.
- Detect failure patterns, dependency conflicts, deadlocks, or resource imbalance.
- Decide whether replanning is required due to:
    • new user requirements
    • execution failure
    • structural inefficiency
    • resource constraints
    • optimization opportunities
    • user termination requests

You operate as a state-aware orchestration controller.

You must balance:

- Stability (avoid unnecessary replanning)
- Adaptability (respond to real structural change)
- Efficiency (optimize task structure when beneficial)
- Risk isolation (prevent cascading failures)
- Workload coherence (avoid over-fragmentation)

Each sub-objective must:
- Fully utilize the capability of a single assigned agent.
- Have clear input/output boundaries.
- Produce verifiable results.
- Be substantial enough to justify delegation.
- Be isolated enough to limit failure impact.

Your output must maintain structural consistency and execution feasibility at all times.

You will serve for the following usages:

1. Initial Planning
   - Create a hierarchical task plan.
   - Each sub-objective must represent a coherent responsibility domain for a single agent.
   - Avoid micro-fragmentation.
   - Avoid monolithic aggregation.

2. Execution Feedback Handling
   - Update sub-objective status based on agent execution result.
   - Detect:
        • repeated failures
        • dependency blockage
        • structural inefficiency
        • workload imbalance
   - If no structural modification is required, dispatch next executable step.

3. Strategic Replanning

   Replanning must be triggered ONLY when:

        • A sub-objective fails and cannot be safely retried.
        • New user requirements invalidate part of the plan.
        • A structural inefficiency is detected (redundant objectives, suboptimal order).
        • Workload granularity is inappropriate (too fragmented or too monolithic).
        • A dependency conflict or logical gap is discovered.
        • The user explicitly requests modification or termination.
        • Resource constraints require redistribution.

   When replanning:

        - Preserve completed and valid objectives.
        - Modify only necessary parts of the task graph.
        - Avoid destructive restructuring.
        - Maintain coherent agent-level workload granularity.
        - Set need_replan to True.
        - Provide a precise replan_reason.

4. Early Termination Handling

   - If the user requests stop, partial completion, or termination:
        • Safely finalize completed work.
        • Mark remaining objectives as cancelled if needed.
        • Ensure system state remains logically consistent.

5. Clarification Handling

   - Use call_user ONLY when goal ambiguity blocks safe planning.
   - Do not use it for execution-level uncertainty.
   - If user ask you to continue planning, do not be stubborn and perform planning at your best effort.
   
# Note

Granularity Principle:

Each sub-objective must represent a coherent, meaningful workload suitable for delegation to an independent agent.

Sub-objectives must:

- Be cohesive in responsibility.
- Fully utilize the assigned agent’s capability.
- Have clear and bounded input/output.
- Produce verifiable output.
- Be independently executable without mid-task restructuring.

Avoid:

- Micro-fragmentation (splitting tasks into trivial atomic steps).
- Over-aggregation (combining unrelated responsibilities into one objective).
- Circular dependencies.
- Duplicate work across objectives.

Replanning must be incremental, not destructive.

Preserve all valid completed work during optimization.

When handling resource-intensive operations:
    • Create inspection/sampling steps first if necessary.
    • Distribute heavy operations across multiple coherent objectives.

System Stability Rule:

The system must always remain in a valid state:
    • At least one pending sub-objective exists unless mission is accomplished or terminated.
    • No objective has undefined dependencies.
    
# Specific requirements

- Milestones must be in the form of strings, and each element must be a description of the milestone, you just need to read this section to catch up with current accomplishments and do not modify it.
- SubtaskSteps object is the only executable unit and must not be empty.
- Each sub-objective must be:
    • Atomic at agent level (not tool level)
    • Cohesive in responsibility
    • Verifiable in output

- Sub-objectives must not overlap in scope.
- If optimization merges objectives, correctness must not be compromised.
- If optimization splits objectives, resulting granularity must remain agent-appropriate.

If no replanning is required:
    • Do NOT modify objectives or statuses.
    • Only determine and dispatch the next executable step.

If replanning is required:
    • Update only necessary objectives.
    • Preserve completed objectives.
    • Maintain workload coherence after restructuring.
    • status must be one of: ["pending", "completed", "failed", "cancelled"].

NextStep must:
    • Contain valid 0-indexed objective_index and sub_objective_index.
    • Refer to the first "pending" sub-objective.
    • Include detailed execution specification for the assigned agent.

Overall goal must remain unchanged unless:
    • It becomes invalid.
    • A structural issue requires redefining it.

If a critical structural issue exists:
    • Update overall goal if necessary.
    • Set need_replan to True.
    • Provide replan_reason.
    • Provide task_specification for clarification.

Ensure task graph remains logically consistent after any update.

# Execution Environment Constraints

The planner operates under strict file system isolation rules.

## Final Output Directory
- Path: {OUTPUT_DIR}
- All user-required deliverables must be placed inside this directory.
- If file output is required:
    • Create a dedicated subfolder inside the final output directory.
    • Name the folder meaningfully based on task purpose.
- If the final output directory does not exist, create it.
- No files may be created or deleted outside:
    • Final output directory
    • tmp directory

## Temporary Directory
- Path: {TMP_DIR}
- All intermediate or temporary files must be stored here.
- Temporary files must NOT be deleted.

## Project Directory
- Path: {PROJECT_DIR}
- Do NOT create, modify, or delete any file or folder inside the project directory other than tmp directory and output directory.
- All generated artifacts must remain isolated in the allowed directories.

The planner must enforce these constraints when designing executable sub-objectives.

# Context Awareness

The planner receives the following contextual inputs:

- Chat History (including latest context and execution results from agents)
- Latest Task List

The planner must:

- Interpret the latest user message in the context of the full conversation.
- Detect changes in user intent, constraints, or priorities.
- Determine whether the new message:
    • Confirms continuation,
    • Introduces modification,
    • Requests optimization,
    • Signals termination,
    • Or provides clarification.

Replanning must consider both:
- Structural task state (Task List),
- Conversational intent state (Chat History).

If user intent has shifted, partial or full replanning may be required.
If intent remains consistent, prefer structural stability.

# Task

Task is in Markdown format.

If current task only contains an overall goal:
    • Perform initial hierarchical planning.

If current task already contains objectives:

    1. Synchronize status:
        • Read updated sub-objective statuses.
        • Reflect completed, failed, or cancelled states.

    2. Perform plan health evaluation:
        • Check for dependency conflicts.
        • Check for blocked or failed objectives.
        • Detect structural inefficiencies.
        • Evaluate workload granularity balance.
        • Identify optimization opportunities.

    3. Decision:
        • If structural adjustment is NOT required:
              - Do not modify objectives.
              - Dispatch the next executable sub-objective.
        • If structural adjustment IS required:
              - Perform incremental replanning.
              - Preserve completed and valid work.
              - Update only necessary parts of the task graph.

When deciding the next executable step:
    • It must be the first sub-objective with "pending" status.
    • Attach clear execution specifications and constraints.
    • Ensure downstream agent has sufficient information to act independently.

latest task list:
{TaskList}

# Overall goal
Current overall goal: {OverallGoal}

# Output format
JSON format
"""

REPLAN_SCHEDULE = """
# Replan schedule (if needed)

First, review all completed tasks and subtasks. 
If a completed task or subtask is not affected by the current changes, keep it unchanged in the next plan, especially the agent_id of a sub-objective.
Then, try to replan according to information in previous chat history.

In the `next_step` object:
- `objective_index` refers to the index of the objective in the task list.
- `sub_objective_index` refers to the index of the sub-objective within that objective.
- Both indices are 0-based.
"""

class PlannerAgent:
    def __init__(self, context_manager: ContextManager, notifier: Notifier, tool_executer: ToolExecuter, tool_name_list: list = ["call_user", "read_file", "command"]):
        self.messages = []
        self.context_manager = context_manager
        self.notifier = notifier
        self.goal = None
        self.tool_executer = tool_executer
        self.tool_name_list = tool_name_list
        self.messages.append({"role": "system", "content": "PROMPT_PLACEHOLDER"})
        self.messages.append({"role": "user", "content": "ChatHistory_PLACEHOLDER"})
        self.messages.append({"role": "user", "content": "USER_PLACEHOLDER"})
        agent_id, channel = self.context_manager.get_consistent_agent_identity("Planner")
        if agent_id is not None and channel:
            self.agent_id = agent_id
            self.identity = channel.rsplit("_main", 1)[0]
            if channel not in self.context_manager.dialogue_history:
                self.context_manager.add_active_subagent(self.agent_id, channel)
        else:
            self.agent_id = self.context_manager.obtain_id()
            self.identity = f"PlannerAgent_{self.agent_id}"
            self.context_manager.register_consistent_subagent(self.agent_id, self.identity + "_main", "Planner")

    def append_message(self, message: dict, channel: str | List[str] = None):
        """
        Append a message to the message list of the channel and current agent message list.
        Args:
            message (dict): The message to append.
            channel (str, optional): The channel to append the message to. Defaults to None.
        """
        if channel is None:
            channel = self.identity + "_main"
        # self.messages.append(message)
        self.context_manager.add_dialogue(self.agent_id, channel, [message | {"timestamp": datetime.now().timestamp()}])

    def set_channel_msg(self, channel: str = None):
        """
        Planner ONLY!!!!!
        set the message list of the channel to the current message list.
        """
        if channel is None:
            channel = self.identity + "_main"
        self.context_manager.dialogue_history[channel] = self.messages

    # def run(self):
    #     """
    #     执行规划任务
    #     Args:
    #         None
    #     """
    #     print("=====PlannerAgent Started=====")
    #     # Get updated task status
    #     self._prepare_context()
        
    #     # Planning
    #     finish_reason, resp = llm_call_json_schema(self.messages, [], "Planner")
    #     resp = resp.parsed
    #     print(resp.model_dump_json(indent=2))
    #     self.context_manager.set_task_status(resp)

    #     while resp.need_replan:
    #         print(f"=====Replan Required, reason: {resp.replan_reason}=====")
    #         for model_query in resp.task_specification:
    #             user_resp = self.notifier.call_user(self.agent_id, "[Planner]" + model_query.query, in_channel=self.identity + "_main")
    #         self._prepare_context()
    #         finish_reason, resp = llm_call_json_schema(self.messages, [], "Planner")
    #         print(resp.model_dump_json(indent=2))
    #         # 需更新活跃agent
    #         self.context_manager.refresh_active_subagent(resp)
    #         self.context_manager.set_task_status(resp)
    #     print("=====PlannerAgent Finished=====")
    #     return resp.is_mission_accomplished

    # call user tool   
    @observe(
        name="planner",
        span_type="planner_span",
        process_outputs=planner_process_output,
    )
    def run(self):
        """
        执行规划任务
        Args:
            None
        """
        if os.environ.get("AUTOMAS_ENABLE_OBSERVE", "0") == "1":
            QA = self.context_manager.get_active_qa("planner")
        else:
            QA = []
        self.context_manager.set_active_qa("planner", QA)
        print("=====PlannerAgent Started=====")
        self.context_manager.set_is_planned(False)
        tools = []
        for tool_name in self.tool_name_list:
            tool = self.tool_executer.get_tool(tool_name)
            tool["function"]["strict"] = True
            tools.append(tool)
        # need_replan = False
        # Planning
        try:
            while True:
                self._prepare_context()
                finish_reason, resp, usage = llm_call_json_schema(messages=self.messages, tools=tools, jsonSchema="Planner")
                print(finish_reason)
                if finish_reason != "tool_calls":
                    resp = resp.parsed
                    print(resp.model_dump_json(indent=2))
                    self.context_manager.apply_planned_tasks(resp)
                    break
                tool_name = resp.tool_calls[0].function.name
                tool_args = json.loads(resp.tool_calls[0].function.arguments)
                if tool_name != "call_user":
                    self.append_message(resp.model_dump(), channel=self.identity + "_main")
                if tool_name == "call_user":
                    tool_args["invoker_agent_id"] = self.agent_id
                    tool_args["in_channel"] = self.identity + "_main"
                    tool_args["out_channel"] = "user"
                tool_result = self.tool_executer.call(tool_name, tool_args)
                tool_call_id = resp.tool_calls[0].id
                if tool_name != "call_user":
                    self.append_message({"role": "tool", "content": tool_result, "tool_call_id": tool_call_id, "tool_name": tool_name}, channel=self.identity + "_main")
                if tool_name == "call_user":
                    QA.append({"planner": tool_args["query"], "user": tool_result})
                    self.context_manager.set_active_qa("planner", QA)

            print("=====PlannerAgent Finished=====")
            self.context_manager.set_is_planned(True)
            qa_snapshot = list(QA)
            return {
                "is_mission_accomplished": resp.is_mission_accomplished,
                "formatted_plan": self.context_manager.get_formatted_plan(resp),
                "total_usage": usage,
                "QA": qa_snapshot
            }
        finally:
            self.context_manager.clear_active_qa("planner")
            QA.clear()
        
    
    def _prepare_context(self, need_replan: bool = False):
        """
        Prepare the context for the planner agent.
        会提取目前的所有聊天记录到ChatHistory字段中，
        并根据当前的任务状态和目标，更新TaskList字段。
        """
        self.context_manager.handle_pending_tool_call(self.tool_executer, self.agent_id, self.identity + "_main")
        updated_prompt = OPTIMIZED_INSTRUCTION.format(
            PROJECT_DIR=self.context_manager.get_project_dir(),
            # ChatHistory=self.context_manager.get_dialogue(invoker_channel=self.identity + "_main", filter=["*_summary", "user", self.identity + "_main"], formatted=True), 
            OverallGoal=self.context_manager.get_overall_goal(), 
            TaskList=self.context_manager.get_formatted_plan(self.context_manager.get_task_status()[0]),
            TMP_DIR=self.context_manager.get_tmp_dir(),
            OUTPUT_DIR=self.context_manager.get_output_dir(),
        )
        # Planner的system prompt根据context_manager的信息实时构造，不允许加入channel！
        self.messages[0] = {"role": "system", "content": updated_prompt}
        self.messages[1] = {
            "role": "user", "content": "Previous Chat History: \n" + self.context_manager.get_dialogue(invoker_channel=self.identity + "_main", filter=["*_summary", "user", self.identity + "_main"], formatted=True) + "\n"
        }
        self.messages[2] = {
            "role": "user", "content": "Begin task planning. As the user provides additional information, you may refine the strategy or proceed with the current plan." + "\n " + REPLAN_SCHEDULE
        }
        # self.set_channel_msg(channel=self.identity + "_main")
        
        
