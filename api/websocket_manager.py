"""
WebSocketManager - WebSocket 连接管理
"""

from typing import Dict, Set
from fastapi import WebSocket


class WebSocketManager:
    """
    WebSocket 连接管理器
    """

    def __init__(self):
        # task_id -> Set[WebSocket]
        self.active_connections: Dict[str, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, task_id: str):
        """
        建立 WebSocket 连接

        Args:
            websocket: WebSocket 对象
            task_id: 任务ID
        """
        await websocket.accept()
        if task_id not in self.active_connections:
            self.active_connections[task_id] = set()
        self.active_connections[task_id].add(websocket)

    def disconnect(self, websocket: WebSocket, task_id: str):
        """
        断开 WebSocket 连接

        Args:
            websocket: WebSocket 对象
            task_id: 任务ID
        """
        if task_id in self.active_connections:
            self.active_connections[task_id].discard(websocket)

    async def broadcast(self, task_id: str, message: dict):
        """
        广播消息给所有连接到该任务的客户端

        Args:
            task_id: 任务ID
            message: 消息内容
        """
        if task_id not in self.active_connections:
            return

        disconnected = set()
        for conn in self.active_connections[task_id]:
            try:
                await conn.send_json(message)
            except Exception:
                disconnected.add(conn)

        # 清理断开的连接
        for conn in disconnected:
            self.active_connections[task_id].discard(conn)

    async def send_to_client(self, websocket: WebSocket, message: dict):
        """
        发送消息给指定客户端

        Args:
            websocket: WebSocket 对象
            message: 消息内容
        """
        try:
            await websocket.send_json(message)
        except Exception as e:
            print(f"Send to client error: {e}")
