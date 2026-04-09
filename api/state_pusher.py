"""
StatePusher - 状态推送管理器
"""

from typing import Optional, Callable, Any
from .state_extractor import StateExtractor
from .state_storage import StateStorage
from .broadcast_queue import get_global_queue


class StatePusher:
    """
    统一状态推送管理器
    在关键节点触发状态推送
    """

    def __init__(self, context_manager, task_id: str, websocket_manager=None):
        """
        初始化 StatePusher

        Args:
            context_manager: ContextManager 实例
            task_id: 任务ID
            websocket_manager: WebSocket 管理器（可选，已弃用，保留参数用于兼容性）
        """
        self.context_manager = context_manager
        self.task_id = task_id
        self.extractor = StateExtractor()
        self._callbacks: list = []  # 额外的回调函数列表

    def add_callback(self, callback: Callable[[str, dict], None]):
        """
        添加状态变更回调函数

        Args:
            callback: 回调函数，参数为 (trigger_reason, state)
        """
        self._callbacks.append(callback)

    def push(self, trigger_reason: str):
        """
        提取状态并推送

        Args:
            trigger_reason: 触发原因

        Returns:
            状态数据
        """
        print(f"[StatePusher] Pushing state for task {self.task_id}, reason: {trigger_reason}")
        
        # 提取状态
        state = self.extractor.extract(self.context_manager, self.task_id)
        print(f"[StatePusher] Extracted state with {len(state.get('chat_body', []))} chat messages")

        # 保存到内存存储
        StateStorage.save(self.task_id, state)
        print(f"[StatePusher] Saved to StateStorage")

        # 将状态放入广播队列（线程安全，供异步上下文消费）
        # 直接传递 state，与 WebSocket 的 get_state 保持一致
        broadcast_q = get_global_queue()
        if broadcast_q:
            try:
                # Manager Queue 的 put 方法没有返回值
                broadcast_q.put({
                    "task_id": self.task_id,
                    "message": state
                })
                print(f"[StatePusher] State queued for broadcast")
            except Exception as e:
                print(f"[StatePusher] Error queuing state: {e}")
        else:
            print("[StatePusher] Warning: broadcast queue not set")

        # 执行额外的回调
        for callback in self._callbacks:
            try:
                callback(trigger_reason, state)
            except Exception as e:
                print(f"Callback error: {e}")

        print(f"[StatePusher] Push completed")
        return state

    def get_current_state(self) -> dict:
        """
        获取当前状态（不触发推送）

        Returns:
            状态数据
        """
        return self.extractor.extract(self.context_manager, self.task_id)
