"""
InputBuffer - 输入缓冲区

使用 multiprocessing.Manager().Queue() 实现跨进程通信
Windows 上 spawn 模式下必须使用 Manager 来共享队列
用于在网页模式下替代命令行输入

设计说明：
- 主进程（server.py）维护 pending_queries 状态字典
- 子进程通过 _register_queue 向主进程注册 query
- 子进程通过 _submit_queue 接收用户响应
- 这种设计避免了跨进程共享复杂状态的问题
"""

import multiprocessing
import threading
import time
from typing import Dict, Optional


# 全局队列实例（在子进程中通过 set_queues 设置）
_global_submit_queue = None
_global_register_queue = None


def set_queues(submit_queue, register_queue):
    """
    设置全局队列（在子进程中调用）

    Args:
        submit_queue: 提交队列（server 写入，子进程读取）
        register_queue: 注册队列（子进程写入，server 读取）
    """
    global _global_submit_queue, _global_register_queue
    _global_submit_queue = submit_queue
    _global_register_queue = register_queue


def get_global_submit_queue():
    """
    获取全局提交队列

    Returns:
        全局队列对象，如果未设置则返回 None
    """
    return _global_submit_queue


def get_global_register_queue():
    """
    获取全局注册队列

    Returns:
        全局队列对象，如果未设置则返回 None
    """
    return _global_register_queue


class InputBuffer:
    """
    输入缓冲区 - 基于 multiprocessing.Manager().Queue() 实现跨进程通信

    设计：
    - 主进程维护 _pending_queries 字典
    - 子进程通过 _register_queue 发送注册请求
    - 子进程通过 _submit_queue 接收响应
    """

    def __init__(self, manager=None):
        """
        初始化输入缓冲区

        Args:
            manager: multiprocessing.Manager 实例，如果为 None 则创建新的 Manager
        """
        # 使用 Manager 创建队列
        if manager is None:
            manager = multiprocessing.Manager()
        self._manager = manager

        # 用户提交响应的队列（server 写入，子进程读取）
        self._submit_queue = manager.Queue()
        # 注册队列（子进程写入，server 读取）- 用于子进程通知主进程有新的 query
        self._register_queue = manager.Queue()

        # 等待中的问题字典（仅在主进程中使用）
        self._pending_queries: Dict[str, str] = {}
        self._pending_lock = threading.Lock()

        # 启动注册消费者线程
        self._running = True
        self._consumer_thread = threading.Thread(target=self._register_consumer, daemon=True)
        self._consumer_thread.start()

    def _register_consumer(self):
        """
        注册消费者线程
        从 _register_queue 读取子进程的注册请求，更新 _pending_queries
        """
        print("[InputBuffer] Register consumer started")
        while self._running:
            try:
                # 非阻塞方式检查队列
                msg = self._register_queue.get(timeout=0.1)
                if msg:
                    task_id = msg.get("task_id")
                    query = msg.get("query")
                    action = msg.get("action", "register")

                    with self._pending_lock:
                        if action == "register":
                            self._pending_queries[task_id] = query
                            print(f"[InputBuffer] Query registered for task {task_id}: {query[:50]}...")
                        elif action == "unregister":
                            self._pending_queries.pop(task_id, None)
                            print(f"[InputBuffer] Query unregistered for task {task_id}")

                    print(f"[InputBuffer] Current pending queries: {list(self._pending_queries.keys())}")
            except:
                # 超时或队列为空，继续循环
                continue

    def stop(self):
        """停止注册消费者线程"""
        self._running = False
        if self._consumer_thread.is_alive():
            self._consumer_thread.join(timeout=1.0)

    def get_submit_queue(self):
        """
        获取提交队列（用于传递给子进程）

        Returns:
            multiprocessing.Queue 对象（实际上是 Manager 代理的队列）
        """
        return self._submit_queue

    def get_register_queue(self):
        """
        获取注册队列（用于传递给子进程）

        Returns:
            multiprocessing.Queue 对象（实际上是 Manager 代理的队列）
        """
        return self._register_queue

    def register_query(self, task_id: str, query: str) -> None:
        """
        注册一个等待用户响应的问题（在主进程中调用）

        Args:
            task_id: 任务ID
            query: 向用户提出的问题
        """
        with self._pending_lock:
            self._pending_queries[task_id] = query
        print(f"[InputBuffer] Query registered for task {task_id}: {query[:50]}...")
        print(f"[InputBuffer] Current pending queries: {list(self._pending_queries.keys())}")

    def wait_for_response(self, task_id: str, timeout: Optional[int] = 600) -> str:
        """
        阻塞等待用户响应（在子进程中调用 - 通过全局函数）

        Args:
            task_id: 任务ID
            timeout: 超时时间（秒），默认10分钟

        Returns:
            用户响应内容

        Raises:
            RuntimeError: 如果没有等待中的问题或队列未设置
        """
        # 从全局队列获取
        global_queue = get_global_submit_queue()
        if global_queue is None:
            raise RuntimeError("Global submit queue not set")

        # 轮询等待响应
        start_time = time.time()
        check_interval = 0.1  # 每100ms检查一次

        while True:
            # 检查是否超时
            if timeout and (time.time() - start_time) > timeout:
                print(f"[InputBuffer] Timeout: {timeout} seconds")
                return "用户未响应，系统继续执行"

            # 尝试从队列获取响应
            try:
                msg = global_queue.get(timeout=check_interval)
                if msg.get("task_id") == task_id:
                    response = msg.get("response", "")
                    print(f"[InputBuffer] Response received for task {task_id}")
                    return response
                else:
                    # 不是当前任务的响应，忽略
                    pass
            except:
                # 队列为空，继续等待
                continue

    def submit_response(self, task_id: str, response: str) -> bool:
        """
        Web API 调用，用户提交响应（在主进程中调用）

        Args:
            task_id: 任务ID
            response: 用户响应内容

        Returns:
            是否成功提交
        """
        # 检查是否有等待中的问题
        with self._pending_lock:
            print(f"[InputBuffer] Current pending queries: {list(self._pending_queries.keys())}")
            if task_id not in self._pending_queries:
                print(f"[InputBuffer] No pending query for task {task_id}")
                return False

        try:
            # 写入提交队列
            self._submit_queue.put({
                "task_id": task_id,
                "response": response
            })

            # 从 pending 中移除
            with self._pending_lock:
                self._pending_queries.pop(task_id, None)

            print(f"[InputBuffer] Response submitted for task {task_id}")
            return True
        except Exception as e:
            print(f"[InputBuffer] Error submitting response: {e}")
            return False

    def get_pending_query(self, task_id: str) -> Optional[str]:
        """
        获取当前等待中的问题（用于前端显示）

        Args:
            task_id: 任务ID

        Returns:
            等待中的问题，如果没有则返回 None
        """
        with self._pending_lock:
            return self._pending_queries.get(task_id)

    def has_pending(self, task_id: str) -> bool:
        """
        检查是否有等待中的问题

        Args:
            task_id: 任务ID

        Returns:
            是否有等待中的问题
        """
        with self._pending_lock:
            return task_id in self._pending_queries


# ============ 全局函数（供子进程使用） ============

def register_query(task_id: str, query: str) -> None:
    """
    全局函数：注册一个等待用户响应的问题（在子进程中使用）
    通过 _register_queue 通知主进程

    Args:
        task_id: 任务ID
        query: 向用户提出的问题
    """
    register_q = get_global_register_queue()
    if register_q is None:
        print(f"[InputBuffer] Error: Register queue not set")
        return

    register_q.put({
        "action": "register",
        "task_id": task_id,
        "query": query
    })
    print(f"[InputBuffer] Query registration sent for task {task_id}: {query[:50]}...")


def wait_for_response(task_id: str, timeout: Optional[int] = 300) -> str:
    """
    全局函数：阻塞等待用户响应（在子进程中使用）

    Args:
        task_id: 任务ID
        timeout: 超时时间（秒），默认5分钟

    Returns:
        用户响应内容

    Raises:
        RuntimeError: 如果队列未设置
    """
    # 从全局队列获取
    global_queue = get_global_submit_queue()
    if global_queue is None:
        raise RuntimeError("Global submit queue not set")

    # 轮询等待响应
    start_time = time.time()
    check_interval = 0.1  # 每100ms检查一次

    while True:
        # 检查是否超时
        if timeout and (time.time() - start_time) > timeout:
            print(f"[InputBuffer] Timeout: {timeout} seconds")
            return "用户未响应，系统继续执行"

        # 尝试从队列获取响应
        try:
            msg = global_queue.get(timeout=check_interval)
            if msg.get("task_id") == task_id:
                response = msg.get("response", "")
                print(f"[InputBuffer] Response received for task {task_id}")
                return response
            else:
                # 不是当前任务的响应，忽略
                pass
        except:
            # 队列为空，继续等待
            continue
