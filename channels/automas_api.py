import asyncio
from dataclasses import dataclass
from typing import Any, Dict, Optional

import httpx


@dataclass(frozen=True)
class TaskStatus:
    task_id: str
    is_running: bool
    is_completed: bool
    is_really_completed: bool
    waiting_for_input: bool
    pending_query: Optional[str]


class AutomasApiClient:
    def __init__(self, base_url: str, timeout_s: float = 10.0):
        self._base_url = base_url.rstrip("/")
        self._client = httpx.AsyncClient(timeout=timeout_s)

    async def aclose(self) -> None:
        await self._client.aclose()

    async def create_task(self, query: str) -> str:
        resp = await self._client.post(f"{self._base_url}/api/tasks", json={"query": query})
        resp.raise_for_status()
        data = resp.json()
        task_id = data.get("task_id")
        if not task_id:
            raise RuntimeError(f"create_task missing task_id: {data!r}")
        return str(task_id)

    async def get_status(self, task_id: str) -> TaskStatus:
        resp = await self._client.get(f"{self._base_url}/api/tasks/{task_id}/status")
        resp.raise_for_status()
        data = resp.json()
        return TaskStatus(
            task_id=str(data.get("task_id", task_id)),
            is_running=bool(data.get("is_running")),
            is_completed=bool(data.get("is_completed")),
            is_really_completed=bool(data.get("is_really_completed")),
            waiting_for_input=bool(data.get("waiting_for_input")),
            pending_query=data.get("pending_query"),
        )

    async def get_state(self, task_id: str) -> Dict[str, Any]:
        resp = await self._client.get(f"{self._base_url}/api/tasks/{task_id}/state")
        resp.raise_for_status()
        return resp.json()

    async def submit_input(self, task_id: str, response: str) -> None:
        resp = await self._client.post(
            f"{self._base_url}/api/tasks/{task_id}/input",
            json={"response": response},
        )
        resp.raise_for_status()

    async def list_task_ids(self) -> list[str]:
        resp = await self._client.get(f"{self._base_url}/api/tasks")
        resp.raise_for_status()
        data = resp.json()
        tasks = data.get("tasks") or []
        ids: list[str] = []
        for t in tasks:
            tid = t.get("task_id")
            if tid:
                ids.append(str(tid))
        return ids

    async def any_running_task_id(self) -> Optional[str]:
        task_ids = await self.list_task_ids()
        for tid in reversed(task_ids):
            try:
                st = await self.get_status(tid)
            except Exception:
                continue
            if st.is_running:
                return tid
        return None

    async def wait_server_ready(self, *, max_wait_s: float = 30.0, interval_s: float = 0.5) -> None:
        deadline = asyncio.get_event_loop().time() + max_wait_s
        last_err: Optional[BaseException] = None
        while asyncio.get_event_loop().time() < deadline:
            try:
                await self.list_task_ids()
                return
            except BaseException as e:
                last_err = e
                await asyncio.sleep(interval_s)
        raise RuntimeError(f"Automas API not ready at {self._base_url}") from last_err

