from operator import sub
from llm.json_schemas import Subtask
from llm.json_schemas import SubtaskSteps
from llm.json_schemas import PlannedTasks
from llm.json_schemas import ResourceReference
from typing import Tuple
from typing import List, Dict, Any, Optional, Literal

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
        
        self.task_state: PlannedTasks = PlannedTasks()

        # 2. 总任务目标 (Global Goal)
        # Refined user requirement
        self.overall_goal: str = ""

        # 3. 可用资源 (Available Resources)
        # Key: Description, Value: Resource URI (URL, File Path)
        self.available_resources: Dict[str, ResourceReference] = {}

        # 4. 对话历史 (Dialogue History)
        self.dialogue_history: List[Dict[str, Any]] = []

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
    
    def set_task_status(self, task_state: PlannedTasks):
        """
        Set the task status.
        """
        self.task_state = task_state
    
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
    
    def get_dialogue(self) -> str:
        """
        Return the dialogue.
        """
        content = "\n".join([
            f"role: {message['role']}, content: {message['content']}" for message in self.dialogue_history
        ])
        return content
    
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
                raise ValueError("Invalid sub-objective index.")
        else:
            print("Invalid objective index.")
            raise ValueError("Invalid objective index.")
                
                
        if task_status == "completed":
            task.finished = all(obj.status == "completed" for obj in task.objective)
            self.task_state.is_mission_accomplished = all(t.finished for t in self.task_state.tasks)

    def set_next_step(self, objective_index: int, sub_objective_index: int):
        """
        Update the next_step indices to point to the next task/sub-objective.
        """
        self.task_state.next_step.objective_index = objective_index
        self.task_state.next_step.sub_objective_index = sub_objective_index
        
    def update_overall_goal(self, overall_goal: str):
        """
        Update the overall goal.
        """
        self.overall_goal = overall_goal
        self.task_state.overall_goal = overall_goal

    def add_available_resources(self, resources: Dict[str, ResourceReference]):
        """
        Add the available resources to the context manager.
        """
        self.available_resources.update(resources)

    def del_available_resources(self, resources: Dict[str, ResourceReference]):
        """
        Delete the available resources from the context manager.
        """
        pop_key = resources.keys()
        for k in pop_key:
            if k in self.available_resources.keys():
                self.available_resources.pop(k)
        
    def add_dialogue(self, dialogue: Dict[str, Any]):
        """
        Add a dialogue message to the dialogue history.
        """
        self.dialogue_history.append(dialogue)
        
    def get_formatted_available_resources(self) -> str:
        """
        Return the formatted available resources string.
        """
        return "\n".join([f"资源描述：{v.description} | 资源URI: {v.URI} | 资源来源类型(type): {v.type}" for k, v in self.available_resources.items()])

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
        """
        markdown_lines = []
        status_str = sub_obj.status
        markdown_lines.append(f"  - [{status_str}] Sub-objective {task_index}.{step_index}: {sub_obj.sub_objective}")
        
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

