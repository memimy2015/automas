from pydantic import BaseModel

class ProacvtiveQuery(BaseModel):
    query: str

class ClaimerSchema(BaseModel):
    need_more_info: bool
    contents: list[ProacvtiveQuery]

class SubtaskSteps(BaseModel):
    sub_objective: str
    status: bool = False

class Subtask(BaseModel):
    objective: list[SubtaskSteps]
    task_name: str
    finished: bool = False

class PlannedTasks(BaseModel):
    tasks: list[Subtask]
    next_step: str