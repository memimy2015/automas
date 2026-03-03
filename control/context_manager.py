from llm.json_schemas import FactoryOutput
import sys
from collections import defaultdict
import os
import fnmatch
from llm.json_schemas import NextStep
from llm.json_schemas import Subtask
from llm.json_schemas import SubtaskSteps
from llm.json_schemas import PlannedTasks
from llm.json_schemas import ResourceReference
from typing import Tuple
from typing import List, Dict, Any, Optional, Literal
from datetime import datetime
from uuid import uuid4
from pydantic import BaseModel
import json

class ContextManager:
    """
    ContextManager class to manage the context of the multi-agent system.
    It maintains the global state including task status, global goal, available resources, and dialogue history.
    """
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        print("=====ContextManager initialized.=====")
        
        # 下一个智能体ID (Agent ID)
        self.next_agent_id: int = 0
        
        # 任务状态 (Task Status)
        self.task_state: PlannedTasks = PlannedTasks()

        # 总任务目标 (Global Goal)
        # Refined user requirement
        self.overall_goal: str = ""
        self.is_clarified: bool = False
        self.is_planned: bool = False
        self.is_executing: bool = False

        # 可用资源 (Available Resources)
        # Key: Description, Value: Resource URI (URL, File Path)
        self.available_resources: Dict[str, ResourceReference] = {}

        # 对话历史 (Dialogue History)
        # Key: Channel, Value: chat history
        # self.dialogue_history: List[Dict[str, Any]] = []
        self.dialogue_history: Dict[str, List[Dict[str, Any]]] = {}
        
        # 项目文件夹
        self.project_dir: str = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.task_dir: str = os.getenv("AUTOMAS_TASK_DIR", "default")
        
        # 活跃的subagent以及他所有的channel
        self.active_subagents: Dict[int, set[str]] = defaultdict(set)
        
        # 固定的subagent以及 default channel
        self.consistent_subagent_id: Dict[int, str] = defaultdict(set)
        
        self.consistentAgent2DefaultChannel: Dict[str, str] = {}
        
        self.auto_dump_enabled: bool = False
        self.auto_dump_dir: Optional[str] = None
        self.auto_dump_run_dir: Optional[str] = None
        self.last_dump_reason: Optional[str] = None
        self.last_dump_params: Optional[Dict[str, Any]] = None
        self.last_dump_filepath: Optional[str] = None
        self.latest_agent_id: Optional[int] = None
        self.latest_agent_tool_usage: Optional[Dict[str, Any]] = None
        self.latest_agent_factory_output: Optional[FactoryOutput] = None
        self.active_qa: Dict[str, List[Dict[str, Any]]] = {}
        self.loaded_from_dump: bool = False
        self.pending_tool_call_channels: set[str] = set()
        
    def register_consistent_subagent(self, agent_id: int, default_channel: str, agent_name: str):
        """
        Register a consistent subagent.
        """
        self.consistent_subagent_id[agent_id] = default_channel
        self.active_subagents[agent_id].add(default_channel)
        self.consistentAgent2DefaultChannel[agent_name] = default_channel
        self._auto_dump("register_consistent_subagent", {"agent_id": agent_id, "channel": default_channel, "name": agent_name})

    def set_latest_agent(self, agent_id: int):
        self.latest_agent_id = agent_id
        self.latest_agent_tool_usage = {
            "agent_id": agent_id,
            "tool_usage": {}
        }
        self._auto_dump("set_latest_agent", {"agent_id": agent_id})

    def record_tool_usage(self, agent_id: int, tool_name: str):
        if self.latest_agent_id != agent_id:
            return
        if not self.latest_agent_tool_usage:
            self.latest_agent_tool_usage = {
                "agent_id": agent_id,
                "tool_usage": {}
            }
        usage = self.latest_agent_tool_usage["tool_usage"]
        usage[tool_name] = usage.get(tool_name, 0) + 1
        self._auto_dump("record_tool_usage", {"agent_id": agent_id, "tool_name": tool_name, "count": usage[tool_name]})

    def get_active_qa(self, kind: Literal["claimer", "planner", "agent"]) -> List[Dict[str, Any]]:
        return list((self.active_qa or {}).get(kind, []) or [])

    def set_active_qa(self, kind: Literal["claimer", "planner", "agent"], qa: List[Dict[str, Any]]):
        qa_value = list(qa or [])
        if not self.active_qa:
            self.active_qa = {}
        self.active_qa[kind] = qa_value
        self._auto_dump("set_active_qa", {"kind": kind, "count": len(qa_value)})

    def clear_active_qa(self, kind: Literal["claimer", "planner", "agent"]):
        if not self.active_qa:
            self.active_qa = {}
        self.active_qa[kind] = []
        self._auto_dump("clear_active_qa", {"kind": kind})
        
    def get_project_dir(self) -> str:
        """
        Return the project directory(AUTOMAS).
        """
        return self.project_dir

    def set_task_dir(self, task_dir: str):
        self.task_dir = task_dir or "default"
        os.makedirs(self.get_tmp_dir(), exist_ok=True)
        os.makedirs(self.get_output_dir(), exist_ok=True)
        self._auto_dump("set_task_dir", {"task_dir": self.task_dir})

    def get_tmp_dir(self) -> str:
        return os.path.join(self.project_dir, "tmp", self.task_dir or "default")

    def get_output_dir(self) -> str:
        return os.path.join(self.project_dir, "output", self.task_dir or "default")

    def get_context(self) -> Dict[str, Any]:
        """
        Return the full context dictionary.
        """
        return {
            "task_state": self.task_state,
            "overall_goal": self.overall_goal,
            "available_resources": self.available_resources,
            "dialogue_history": self.dialogue_history
        }

    def get_task_status(self) -> Tuple[PlannedTasks, str]:
        """
        Return the current task status and its JSON string representation.
        """
        return self.task_state, self.task_state.model_dump_json(indent=2)

    def set_is_planned(self, is_planned: bool):
        self.is_planned = is_planned
        self._auto_dump("set_is_planned", {"is_planned": is_planned})

    def handle_pending_tool_call(self, tool_executer, agent_id: int, channel: str):
        if not self.loaded_from_dump:
            return
        if channel in self.pending_tool_call_channels:
            return
        messages = self.dialogue_history.get(channel, [])
        if not messages:
            return
        last_message = messages[-1]
        tool_calls = last_message.get("tool_calls") if isinstance(last_message, dict) else None
        if not tool_calls:
            return
        tool_call = tool_calls[0]
        function_info = tool_call.get("function", {})
        tool_name = function_info.get("name")
        if not tool_name:
            return
        tool_args = json.loads(function_info.get("arguments", "{}"))
        if tool_name == "call_user":
            tool_args["invoker_agent_id"] = agent_id
            tool_args["in_channel"] = channel
            tool_args["out_channel"] = "user"
        tool_result = tool_executer.call(tool_name, tool_args)
        if tool_name != "call_user":
            self.add_dialogue(
                agent_id,
                channel,
                [{"role": "tool", "content": tool_result, "tool_call_id": tool_call.get("id"), "tool_name": tool_name} | {"timestamp": datetime.now().timestamp()}],
            )
        self.pending_tool_call_channels.add(channel)
    
    def obtain_id(self):
        """
        Obtain a new agent ID.
        """
        if os.getenv("IS_DEBUG_ENABLED", "1") == "1":
            if not self.is_executing:
                self.next_agent_id += 1
            self._auto_dump("obtain_id", {"next_agent_id": self.next_agent_id})
        return self.next_agent_id
        
    def set_task_status(self, task_state: PlannedTasks, dump: bool = True):
        """
        Set the task status.
        """
        self.task_state = task_state
        self.overall_goal = task_state.overall_goal
        self.verify_index()
        if dump:
            self._auto_dump("set_task_status", {"overall_goal": task_state.overall_goal})
        
    def verify_index(self):
        task = self.task_state
        idx_i, idx_j = self._get_current_indices()
        for i, subtask in enumerate(task.tasks):
            for j, sub_objective in enumerate(subtask.objective):
                if sub_objective.status == "pending":
                    # if i != idx_i or j != idx_j:
                    #     print(f"Current index: {idx_i}, {idx_j}, expected index {i}, {j}")
                    assert i == idx_i and j == idx_j, f"Current index: {idx_i}, {idx_j}, expected index {i}, {j}"
                    print(f"Current index: {idx_i}, {idx_j}, expected index {i}, {j}")
                    task.next_step = NextStep(
                        objective_index=i,
                        sub_objective_index=j,
                    )
                    return
    
    def get_overall_goal(self) -> str:
        """
        Return the overall goal.
        """
        return self.overall_goal
    
    def get_available_resources(self) -> Dict[str, ResourceReference]:
        """
        Return the available resources.
        """
        return self.available_resources
    
    def get_dialogue(self, invoker_channel: str, filter: List[str] = None, formatted: bool = False) -> str | List[Dict[str, Any]]:
        """
        Return the dialogue with filtered message. It WILL NOT add system prompt from other channel!
        Args:
            filter: List[str] = None, filter the channels to include, empty for all channels.
        Returns:
            str | List[Dict[str, Any]]: the dialogue or raw messages.
        """
        patterns = list(filter or [])
        def is_included(channel_name: str) -> bool:
            if not patterns:
                return True
            for pattern in patterns:
                # if fnmatch.fnmatchcase(channel_name, pattern): # case sensitive
                if fnmatch.fnmatch(channel_name, pattern):
                    return True
            return False
        messages = []
        for channel in self.dialogue_history:
            if is_included(channel):
                channel_messages = self.dialogue_history.get(channel, [])
                if not channel_messages:
                    continue
                if channel == invoker_channel:
                    messages.extend(channel_messages)
                else:
                    messages.extend([m for m in channel_messages if m.get("role") != "system"])
        
        messages = sorted(messages, key=lambda x: x.get("timestamp", 0))
        if formatted:
            lines = []
            for message in messages:
                s = ", ".join([f"{k}: {v}" for k, v in message.items() if k != "timestamp" and k != "usage"])
                lines.append(s)
            return "\n".join(lines)
        else:
            new_messages = []
            for message in messages:
                new_messages.append({k: v for k, v in message.items() if k != "timestamp" and k != "usage"})
            return new_messages
        
    
    def _get_current_indices(self) -> Tuple[int, int]:
        """Helper to get current objective and sub-objective indices."""
        idx = self.task_state.next_step
        return idx.objective_index, idx.sub_objective_index

    def add_milestone(self, milestone: str):
        """
        Add a milestone string to the current sub-objective's milestones list.
        """
        obj_idx, sub_idx = self._get_current_indices()
        if 0 <= obj_idx < len(self.task_state.tasks):
            task = self.task_state.tasks[obj_idx]
            if 0 <= sub_idx < len(task.objective):
                task.objective[sub_idx].milestones.append(milestone)
                self._auto_dump("add_milestone", {"milestone": milestone})

    def submit_sub_objective(self, task_summary: str, task_status: Literal["pending", "completed", "failed", "cancelled"], files: Dict[str, ResourceReference]):
        """
        Submit a sub-objective to the task list. which will check for status update for the whole task.
        """
        obj_idx, sub_idx = self._get_current_indices()
        if 0 <= obj_idx < len(self.task_state.tasks):
            task: Subtask = self.task_state.tasks[obj_idx]
            if 0 <= sub_idx < len(task.objective):
                sub_objective: SubtaskSteps = task.objective[sub_idx]
                sub_objective.status = task_status
                sub_objective.execution_summary = task_summary
                cur_resources = set()
                for cur_res in sub_objective.resource_reference:
                    cur_resources.add(cur_res.description)
                    cur_resources.add(cur_res.URI)
                sub_objective.resource_reference.extend([v for v in files.values() if v.description not in cur_resources and v.URI not in cur_resources])
                self.add_available_resources(files)
                print(f"Submitted to {obj_idx + 1}.{sub_idx + 1} {sub_objective.sub_objective}")
            else:
                print("Invalid sub-objective index.")
                self._auto_dump("submit_sub_objective", {"error": "Invalid sub-objective index."})
                raise ValueError("Invalid sub-objective index.")
        else:
            print("Invalid objective index.")
            self._auto_dump("submit_sub_objective", {"error": "Invalid sub-objective index."})
            raise ValueError("Invalid objective index.")
                
                
        if task_status == "completed":
            task.finished = all(obj.status == "completed" for obj in task.objective)
            self.task_state.is_mission_accomplished = all(t.finished for t in self.task_state.tasks)
        self.is_executing = False
        self.is_planned = False
        self._auto_dump("submit_sub_objective", {"status": task_status})

    def set_next_step(self, objective_index: int, sub_objective_index: int):
        """
        Update the next_step indices to point to the next task/sub-objective.
        """
        self.task_state.next_step.objective_index = objective_index
        self.task_state.next_step.sub_objective_index = sub_objective_index
        self._auto_dump("set_next_step", {"objective_index": objective_index, "sub_objective_index": sub_objective_index})
        
    def update_overall_goal(self, overall_goal: str):
        """
        Update the overall goal.
        """
        self.overall_goal = overall_goal
        self.task_state.overall_goal = overall_goal
        self._auto_dump("update_overall_goal", {"overall_goal": overall_goal})

    def add_available_resources(self, resources: Dict[str, ResourceReference]):
        """
        Add the available resources to the context manager.
        """
        self.available_resources.update(resources)
        self._auto_dump("add_available_resources", {"keys": list(resources.keys())})

    def del_available_resources(self, resources: Dict[str, ResourceReference]):
        """
        Delete the available resources from the context manager.
        """
        pop_key = resources.keys()
        for k in pop_key:
            if k in self.available_resources.keys():
                self.available_resources.pop(k)
        self._auto_dump("del_available_resources", {"keys": list(resources.keys())})
        
    def add_dialogue(self, agent_id: int, channel: str | List[str], dialogue: List[Dict[str, Any]]):
        """
        Add a dialogue message to the dialogue history.
        If agent is inactive, raise **ValueError**.
        If channel is not active, this function will **create a new channel** by add_active_subagent_channel.
        """
        if self.active_subagents.get(agent_id, None) is None:
            print(f"Agent {agent_id} is not active.")
            raise ValueError(f"Agent {agent_id} is not active.")
        if isinstance(channel, str):
            channel = [channel]
        for c in channel:
            if c not in self.dialogue_history.keys():
                self.dialogue_history[c] = []
                self.add_active_subagent_channel(agent_id, c)
                print(f"Add channel: {c} to dialogue history.")
            self.dialogue_history[c].extend(dialogue)       
        self._auto_dump("add_dialogue", {"channel": channel})

    def record_agent_factory_output(self, output: FactoryOutput):
        self.latest_agent_factory_output = output
        self._auto_dump("record_agent_factory_output", {"role_setting": output.role_setting, "task_specification": output.task_specification})
        
    def get_formatted_available_resources(self) -> str:
        """
        Return the formatted available resources string.
        """
        return "\n".join([f"可用资源描述：{v.description} | 资源URI: {v.URI} | 资源来源类型(type): {v.type}" for k, v in self.available_resources.items()])

    def get_formatted_plan(self, plan: PlannedTasks) -> str:
        """
        Convert a PlannedTasks object into a Markdown formatted string.
        Includes full status information and resource references.
        """
        markdown_lines = []
        for i, task in enumerate(plan.tasks, 1):
            markdown_lines.append(self.get_formatted_subtask(task, i))
            
        if hasattr(plan, 'overall_goal') and plan.overall_goal:
            markdown_lines.append(f"**Overall Goal**: {plan.overall_goal}")
        return "\n".join(markdown_lines)
    
    def get_formatted_subtask(self, task: Subtask, index: int) -> str:
        """
        Convert a Subtask object into a Markdown formatted string.
        Args:
            task: The Subtask object to convert.
            index: The index of the task (1-based).
        Returns:
            A string in Markdown format representing the Subtask object.
        """
        markdown_lines = []
        task_finished_mark = "[x]" if task.finished else "[ ]"
        markdown_lines.append(f"- {task_finished_mark} **Task {index}: {task.task_name}**")
        
        if hasattr(task, 'resource_reference') and task.resource_reference:
                markdown_lines.append(f"  > **Resource References**:")
                for ref in task.resource_reference:
                    markdown_lines.append(f"    - [{ref.type}] {ref.description}: {ref.URI}")

        for j, sub_obj in enumerate(task.objective, 1):
            markdown_lines.append(self.get_formatted_subtask_step(sub_obj, index, j))
            
        return "\n".join(markdown_lines)

    def get_formatted_subtask_step(self, sub_obj: SubtaskSteps, task_index: int, step_index: int) -> str:
        """
        Convert a SubtaskSteps object into a Markdown formatted string.
        Args:
            sub_obj: The SubtaskSteps object to convert.
            task_index: The index of the task (1-based).
            step_index: The index of the sub-objective (1-based).
        Returns:
            A string in Markdown format representing the SubtaskSteps object.
        """
        markdown_lines = []
        status_str = sub_obj.status
        markdown_lines.append(f"  - [{status_str}] Sub-objective {task_index}.{step_index}: {sub_obj.sub_objective} (Executed by Agent (ID): {sub_obj.agent_id})")
        
        if sub_obj.milestones:
            for milestone in sub_obj.milestones:
                markdown_lines.append(f"    - {milestone}")
        
        if hasattr(sub_obj, 'resource_reference') and sub_obj.resource_reference:
            markdown_lines.append(f"    > **Resource References**:")
            for ref in sub_obj.resource_reference:
                markdown_lines.append(f"      - [{ref.type}] {ref.description}: {ref.URI}")
                
        return "\n".join(markdown_lines)

    def get_subtask(self, task_index: int) -> Subtask:
        """
        Return the Subtask object at the given index (0-based).
        """
        return self.task_state.tasks[task_index]
    
    def get_subtask_step(self, task_index: int, step_index: int) -> SubtaskSteps:
        """
        Return the SubtaskSteps object at the given index (0-based).
        """
        return self.task_state.tasks[task_index].objective[step_index]
    
    def is_accomplished(self) -> bool:
        """
        Return the overall task completion status.
        """
        return self.task_state.is_mission_accomplished
    
    def add_active_subagent(self, subagent_id: int, default_channel: str):
        """
        Add an active subagent and its default channel.
        """
        if subagent_id not in self.active_subagents:
            self.active_subagents[subagent_id] = set()
            print(f"Add subagent {subagent_id} to active subagents.")
        self.active_subagents[subagent_id].add(default_channel)
        self._auto_dump("add_active_subagent", {"subagent_id": subagent_id, "channel": default_channel})
        
    def add_active_subagent_channel(self, subagent_id: int, channel: str):
        """
        Add an active channel for the subagent.
        """
        if subagent_id in self.active_subagents:
            if channel not in self.active_subagents[subagent_id]:
                self.active_subagents[subagent_id].add(channel)
                self._auto_dump("add_active_subagent_channel", {"subagent_id": subagent_id, "channel": channel})
        else:
            print(f"Subagent {subagent_id} not found in active subagents.")
            raise ValueError(f"Subagent {subagent_id} not found in active subagents.")

    def del_active_subagent_channel(self, subagent_id: int, channel: str):
        """
        Delete an active channel for the subagent.
        """
        if subagent_id in self.active_subagents:
            if channel in self.active_subagents[subagent_id]:
                self.active_subagents[subagent_id].remove(channel)
                self._auto_dump("del_active_subagent_channel", {"subagent_id": subagent_id, "channel": channel})
            else:
                print(f"Channel {channel} not found in active channels of subagent {subagent_id}.")
        else:
            print(f"Subagent {subagent_id} not found in active subagents.")

    def del_active_subagent(self, subagent_id: int):
        """
        Delete an active subagent and its all channels.
        """
        if subagent_id in self.active_subagents:
            self.active_subagents[subagent_id].clear()
            self._auto_dump("del_active_subagent", {"subagent_id": subagent_id})
        else:
            print(f"Subagent {subagent_id} not found in active subagents.")
        
    def refresh_active_subagent(self, resp: PlannedTasks, dump: bool = True):
        """
        Refresh the active subagents based on the planned tasks.
        """
        print("===========================Refresh active subagents===========================")
        current_activate_agent = list(self.consistent_subagent_id)
        for task in resp.tasks:
            for sub_task in task.objective:
                if sub_task.status == "completed":
                    current_activate_agent.append(sub_task.agent_id)
        self.active_subagents = {k: v for k, v in self.active_subagents.items() if k in current_activate_agent}
        print(f"=====Active subagents=====: \n {self.active_subagents.keys()}")
        channel_ls = []
        for subagent_id, channels in self.active_subagents.items():
            for channel in channels:
                channel_ls.append(channel)
        self.dialogue_history = {k: v for k, v in self.dialogue_history.items() if k in channel_ls}
        print("===========================Refresh active subagents END===========================")
        if dump:
            self._auto_dump("refresh_active_subagent", {"active_subagents": list(self.active_subagents.keys())})

    def apply_planned_tasks(self, resp: PlannedTasks):
        self.set_task_status(resp, dump=False)
        # if need_replan:
        self.refresh_active_subagent(resp, dump=False)
        self._auto_dump("apply_planned_tasks", {})
        
    def clear_active_subagents(self):
        """
        Clear all active subagents and their channels.
        """
        self.active_subagents.clear()
        self._auto_dump("clear_active_subagents", {})
        
    def set_current_subtask_agent_id(self,agent_id: int):
        """
        Set the agent_id for the current sub-objective.
        """
        sub_objective_index, sub_objective_step_index = self._get_current_indices()
        self.task_state.tasks[sub_objective_index].objective[sub_objective_step_index].agent_id = agent_id
        self._auto_dump("set_current_subtask_agent_id", {"agent_id": agent_id})
    
    def dump(self, path: Optional[str] = None, reason: Optional[str] = None, params: Optional[Dict[str, Any]] = None):
        """
        Dump the current context manager state.
        """
        if path is None:
            path = self._build_dump_path(self.auto_dump_dir, reason)
        self.last_dump_reason = reason
        self.last_dump_params = params
        self.last_dump_filepath = path
        # print(f"Dumping context manager state to {path}\n Reason: {reason}\n Params: {params}\n")
        context = self._to_serializable(self._get_dump_state())
        with open(path, "w", encoding="utf-8") as f:
            json.dump(context, f, indent=2, ensure_ascii=False)

    def enable_auto_dump(self, dump_dir: Optional[str] = None):
        self.auto_dump_enabled = True
        self.auto_dump_dir = dump_dir
        base_dir = dump_dir or os.path.join(self.project_dir, "dump")
        run_id = f"{self._format_date()}_{uuid4()}"
        self.auto_dump_run_dir = os.path.join(base_dir, run_id)

    def disable_auto_dump(self):
        self.auto_dump_enabled = False

    def load(self, path: str):
        """
        Load the context manager state from a file.
        """
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        dump_meta = data.get("dump_meta", {})
        self.loaded_from_dump = True
        self.next_agent_id = data.get("next_agent_id", self.next_agent_id)
        self.overall_goal = data.get("overall_goal", self.overall_goal)
        self.is_clarified = data.get("is_clarified", self.is_clarified)
        self.is_planned = data.get("is_planned", self.is_planned)
        self.is_executing = data.get("is_executing", self.is_executing)
        self.project_dir = data.get("project_dir", self.project_dir)
        self.task_dir = data.get("task_dir", self.task_dir)
        self.available_resources = self._restore_available_resources(data.get("available_resources", {}))
        self.dialogue_history = data.get("dialogue_history", {})
        self.active_subagents = self._restore_active_subagents(data.get("active_subagents", {}))
        self.consistent_subagent_id = self._restore_consistent_subagents(data.get("consistent_subagent_id", {}))
        self.consistentAgent2DefaultChannel = data.get("consistentAgent2DefaultChannel", {})
        self.auto_dump_enabled = data.get("auto_dump_enabled", self.auto_dump_enabled)
        self.auto_dump_dir = data.get("auto_dump_dir", self.auto_dump_dir)
        if not self.auto_dump_run_dir:
            self.auto_dump_run_dir = data.get("auto_dump_run_dir", self.auto_dump_run_dir)
        self.last_dump_reason = data.get("last_dump_reason", dump_meta.get("reason", self.last_dump_reason))
        self.last_dump_params = data.get("last_dump_params", dump_meta.get("params", self.last_dump_params))
        self.last_dump_filepath = data.get("last_dump_filepath", self.last_dump_filepath)
        self.latest_agent_id = data.get("latest_agent_id", self.latest_agent_id)
        self.latest_agent_tool_usage = data.get("latest_agent_tool_usage", self.latest_agent_tool_usage)
        self.latest_agent_factory_output = self._restore_factory_output(data.get("latest_agent_factory_output", self.latest_agent_factory_output))
        self.active_qa = data.get("active_qa", self.active_qa) or {}
        os.makedirs(self.get_tmp_dir(), exist_ok=True)
        os.makedirs(self.get_output_dir(), exist_ok=True)
        task_state_data = data.get("task_state")
        if task_state_data is not None:
            self.task_state = self._restore_planned_tasks(task_state_data)
        self.verify_index()

    def _get_dump_state(self) -> Dict[str, Any]:
        return {
            "dump_meta": {
                "timestamp_ms": self._format_timestamp_ms(),
                "reason": self.last_dump_reason,
                "params": self.last_dump_params
            },
            "auto_dump_enabled": self.auto_dump_enabled,
            "auto_dump_dir": self.auto_dump_dir,
            "auto_dump_run_dir": self.auto_dump_run_dir,
            "last_dump_reason": self.last_dump_reason,
            "last_dump_params": self.last_dump_params,
            "last_dump_filepath": self.last_dump_filepath,
            "latest_agent_id": self.latest_agent_id,
            "latest_agent_tool_usage": self.latest_agent_tool_usage,
            "latest_agent_factory_output": self.latest_agent_factory_output,
            "active_qa": self.active_qa,
            "next_agent_id": self.next_agent_id,
            "task_state": self.task_state,
            "overall_goal": self.overall_goal,
            "is_clarified": self.is_clarified,
            "is_planned": self.is_planned,
            "is_executing": self.is_executing,
            "available_resources": self.available_resources,
            "dialogue_history": self.dialogue_history,
            "active_subagents": self.active_subagents,
            "consistent_subagent_id": self.consistent_subagent_id,
            "consistentAgent2DefaultChannel": self.consistentAgent2DefaultChannel,
            "project_dir": self.project_dir,
            "task_dir": self.task_dir
        }

    def _auto_dump(self, reason: Optional[str] = None, params: Optional[Dict[str, Any]] = None):
        if os.getenv("IS_DEBUG_ENABLED", "1") != "1":
            return
        if not self.auto_dump_enabled:
            return
        path = self._build_dump_path(self.auto_dump_dir, reason)
        self.dump(path, reason=reason, params=params)

    def _format_timestamp_ms(self) -> str:
        now = datetime.now()
        return now.strftime("%Y%m%d_%H%M%S_") + f"{int(now.microsecond / 1000):03d}"

    def _sanitize_reason(self, reason: str) -> str:
        return "".join([c if c.isalnum() or c in ("-", "_") else "_" for c in reason])

    def _build_dump_path(self, dump_dir: Optional[str], reason: Optional[str]) -> str:
        if dump_dir is None:
            dump_dir = self.auto_dump_run_dir or os.path.join(self.project_dir, "dump")
        if self.auto_dump_run_dir and not dump_dir.startswith(self.auto_dump_run_dir):
            dump_dir = self.auto_dump_run_dir
        os.makedirs(dump_dir, exist_ok=True)
        timestamp = self._format_timestamp_ms()
        reason_tag = self._sanitize_reason(reason) if reason else "unknown"
        return os.path.join(dump_dir, f"context_{timestamp}_{reason_tag}.json")

    def _format_date(self) -> str:
        now = datetime.now()
        return now.strftime("%Y%m%d_%H%M%S")

    def get_consistent_agent_identity(self, agent_name: str) -> Tuple[Optional[int], Optional[str]]:
        channel = self.consistentAgent2DefaultChannel.get(agent_name)
        if not channel:
            return None, None
        agent_id = self._get_agent_id_by_channel(channel)
        return agent_id, channel

    def _get_agent_id_by_channel(self, channel: str) -> Optional[int]:
        for agent_id, stored_channel in self.consistent_subagent_id.items():
            if stored_channel == channel:
                return agent_id
        return None

    def _restore_planned_tasks(self, data: Any) -> PlannedTasks:
        if isinstance(data, PlannedTasks):
            return data
        if hasattr(PlannedTasks, "model_validate"):
            return PlannedTasks.model_validate(data)
        if hasattr(PlannedTasks, "parse_obj"):
            return PlannedTasks.parse_obj(data)
        return PlannedTasks(**data)
    
    def _restore_factory_output(self, data: Any) -> FactoryOutput:
        if isinstance(data, FactoryOutput):
            return data
        if hasattr(FactoryOutput, "model_validate"):
            return FactoryOutput.model_validate(data)
        if hasattr(FactoryOutput, "parse_obj"):
            return FactoryOutput.parse_obj(data)
        return FactoryOutput(**data)
    
    def _restore_available_resources(self, data: Dict[str, Any]) -> Dict[str, ResourceReference]:
        resources = {}
        for key, value in data.items():
            if isinstance(value, ResourceReference):
                resources[key] = value
            elif isinstance(value, dict):
                resources[key] = ResourceReference(**value)
            else:
                resources[key] = value
        return resources

    def _restore_active_subagents(self, data: Dict[str, Any]) -> Dict[int, set[str]]:
        restored = defaultdict(set)
        for key, value in data.items():
            restored[int(key)] = set(value or [])
        return restored

    def _restore_consistent_subagents(self, data: Dict[str, Any]) -> Dict[int, str]:
        restored = {}
        for key, value in data.items():
            restored[int(key)] = value
        return restored

    def _to_serializable(self, value: Any):
        if isinstance(value, BaseModel):
            return value.model_dump()
        if isinstance(value, dict):
            return {k: self._to_serializable(v) for k, v in value.items()}
        if isinstance(value, (list, tuple, set)):
            return [self._to_serializable(v) for v in value]
        return value
