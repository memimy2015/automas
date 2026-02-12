from pydantic import BaseModel, Field
from uuid import uuid4
from typing import Literal
class ProacvtiveQuery(BaseModel):
    query: str

class ResourceReference(BaseModel):
    description: str = Field(..., description="资源的描述", required=True)
    URI: str = Field(..., description="资源的URI", required=True)
    type: Literal["from_user", "from_memorybase", "from_agent"] = Field(description="资源的来源类型", required=True, default="from_user")

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
    status: Literal["pending", "completed", "failed", "cancelled"] = "pending"
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
    
class SubmitMessage(BaseModel):
    task_name: str = Field(..., description="当前任务名称", required=True)
    task_summary: str = Field(..., description="当前任务的摘要, 可以参考过往的信息", required=True)
    task_status: Literal["pending", "completed", "failed", "cancelled"] = Field(..., description="当前任务的状态", required=True)
    resource_reference: list[ResourceReference] = Field(description="当前任务的资源引用", default_factory=list)
