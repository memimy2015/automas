"""
BroadcastQueue - 广播队列

使用 multiprocessing.Manager().Queue() 实现跨进程通信
Windows 上 spawn 模式下必须使用 Manager 来共享队列
"""

import multiprocessing
from typing import Dict, Any, Optional


class BroadcastQueue:
    """
    广播队列 - 基于 multiprocessing.Manager().Queue() 实现跨进程通信

    使用 Manager 创建的队列可以在 Windows spawn 模式下正确传递
    """

    def __init__(self, manager=None):
        """
        初始化广播队列

        Args:
            manager: multiprocessing.Manager 实例，如果为 None 则创建新的 Manager
        """
        # 使用 Manager 创建队列
        if manager is None:
            manager = multiprocessing.Manager()
        self._manager = manager
        self._queue = manager.Queue()

    def get_queue(self):
        """
        获取队列对象（用于传递给子进程）

        Returns:
            multiprocessing.Queue 对象（实际上是 Manager 代理的队列）
        """
        return self._queue

    def put(self, task_id: str, message: dict) -> bool:
        """
        将消息放入队列

        Args:
            task_id: 任务ID
            message: 消息内容（状态数据）

        Returns:
            是否成功放入队列
        """
        try:
            # 放入队列的数据包含 task_id 和 message
            self._queue.put({
                "task_id": task_id,
                "message": message
            })
            print(f"[BroadcastQueue] State queued for task {task_id}")
            return True
        except Exception as e:
            print(f"[BroadcastQueue] Error putting message: {e}")
            return False

    def get(self, timeout: float = 0.1) -> Optional[Dict[str, Any]]:
        """
        从队列获取一条消息

        Args:
            timeout: 超时时间（秒）

        Returns:
            消息数据，超时返回 None
        """
        try:
            return self._queue.get(timeout=timeout)
        except:
            return None


# 全局队列实例（在子进程中通过 set_queue 设置）
_global_queue = None


def set_queue(queue):
    """
    设置全局队列（在子进程中调用）

    Args:
        queue: multiprocessing.Queue 对象（或 Manager 代理的队列）
    """
    global _global_queue
    _global_queue = queue


def get_global_queue():
    """
    获取全局队列

    Returns:
        全局队列对象，如果未设置则返回 None
    """
    return _global_queue
