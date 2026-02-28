from typing import Optional
from pydantic import BaseModel, Field
from uuid import uuid4
from typing import Literal
class ProactiveQuery(BaseModel):
    query: str = Field(description="向用户提出询问补充信息的问题", default="")

class ResourceReference(BaseModel):
    description: str = Field(..., description="资源的描述", required=True)
    URI: str = Field(..., description="资源的URI", required=True)
    type: Literal["from_user", "from_memorybase", "from_agent"] = Field(description="资源的来源类型", required=True, default="from_user")

class ClaimerSchema(BaseModel):
    need_more_info: bool = Field(default=False, description="是否需要更多信息")
    contents: list[ProactiveQuery] = Field(description="为了补充不足的信息而用户提出的问题列表", default_factory=list)
    refined_objective: str = Field(description="用户对任务的完善描述", default="")
    resource_reference: list[ResourceReference] = Field(description="用户对任务的完善描述的资源引用", default_factory=list)

class SubtaskResults(BaseModel):
    Summary: str = Field(description="子任务的摘要", default="")
    CreatedResource: list[ResourceReference] = Field(description="新创建的资源引用,类型一定是from_agent", default_factory=list)

class SubtaskSteps(BaseModel):
    sub_objective: str = Field(description="子任务的子步骤描述", default="")
    status: Literal["pending", "completed", "failed", "cancelled"] = Field(description="子任务的子步骤的状态", default="pending")
    milestones: list[str] = Field(description="子任务的子步骤的里程碑信息", default_factory=list)
    resource_reference: list[ResourceReference] = Field(description="子任务的子步骤的资源引用", default_factory=list)
    execution_summary: str = Field(description="子任务的子步骤的执行摘要", default="")
    agent_id: Optional[int] = Field(description="执行子任务的智能体的ID，如果子任务还没开始就不需要设置，已经完成的子任务会包含这个字段，你只需要保持原样。", default=None)

class Subtask(BaseModel):
    objective: list[SubtaskSteps] = Field(description="子任务的步骤列表", default_factory=list)
    task_name: str = Field(description="子任务的名称", default="")
    finished: bool = Field(default=False, description="子任务是否完成")
    resource_reference: list[ResourceReference] = Field(description="子任务的资源引用", default_factory=list)

class NextStep(BaseModel):
    objective_index: int = Field(default=0, description="子任务的索引，从0开始")
    sub_objective_index: int = Field(default=0, description="子任务的子步骤的索引，从0开始")

class PlannedTasks(BaseModel):
    tasks: list[Subtask]= Field(description="子任务列表", default_factory=list)
    next_step: NextStep = Field(default=NextStep(), description="下一个执行的子任务以及子任务的子步骤的索引")
    need_replan: bool = Field(default=False, description="是否需要重新规划")
    is_mission_accomplished: bool = Field(default=False, description="是否所有子任务都已完成")
    overall_goal: str = Field(description="总目标", default="")
    replan_reason: str = Field(description="重新规划的原因", default="")
    task_specification: list[ProactiveQuery] = Field(description="重新规划的任务时，以提问方式向用户询问需要补充的信息的列表，提问最好给出选项。", default_factory=list)
    
class FactoryOutput(BaseModel):
    role_setting: str = Field(description="角色身份信息的设置", default="")
    task_specification: str = Field(description="给出任务的更多信息，如使命、能力边界(如访问权限之类的)、任务注意事项、可能出现的问题和解决方案。markdown格式，注意换行。", default="")
    
class SubmitMessage(BaseModel):
    task_name: str = Field(..., description="当前任务名称", required=True)
    task_summary: str = Field(..., description="当前任务的摘要, 可以参考过往的信息", required=True)
    task_status: Literal["pending", "completed", "failed", "cancelled"] = Field(..., description="当前任务的状态", required=True)
    resource_reference: list[ResourceReference] = Field(description="当前任务的资源引用", default_factory=list)
