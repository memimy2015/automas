from pydantic import BaseModel
from typing import Literal
class ProacvtiveQuery(BaseModel):
    query: str

class ResourceReference(BaseModel):
    description: str = None
    URI: str = None
    type: Literal["from_user", "from_memorybase", "from_agent"] = "from_user"

class ClaimerSchema(BaseModel):
    need_more_info: bool
    contents: list[ProacvtiveQuery]
    refined_objective: str = None
    resource_reference: list[ResourceReference] = []

class SubtaskResults(BaseModel):
    Summary: str = ""
    CreatedResource: list[ResourceReference] = [] # 新创建的资源引用,类型一定是from_agent

class SubtaskSteps(BaseModel):
    sub_objective: str = ""
    status: Literal["pending", "completed", "stopped", "cancelled"] = "pending"
    milestones: list[str] = []
    resource_reference: list[ResourceReference] = []
    execution_summary: str = ""

class Subtask(BaseModel):
    objective: list[SubtaskSteps] = []
    task_name: str = ""
    finished: bool = False
    resource_reference: list[ResourceReference] = []

class NextStep(BaseModel):
    objective_index: int = 0
    sub_objective_index: int = 0

class PlannedTasks(BaseModel):
    tasks: list[Subtask]= []
    next_step: NextStep = NextStep()
    need_replan: bool = False
    is_mission_accomplished: bool = False
    overall_goal: str = ""
    replan_reason: str = ""
    task_specification: list[ProacvtiveQuery] = []
    
class FactoryOutput(BaseModel):
    role_setting: str = ""
    task_specification: str = ""
