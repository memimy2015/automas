"""
FastAPI 服务 - 提供 HTTP API 和 WebSocket 支持
使用 multiprocessing.Manager().Queue() 实现跨进程通信
Windows 上 spawn 模式下必须使用 Manager 来共享队列
"""

import os
import sys
import uuid
import asyncio
import multiprocessing
from typing import Dict, Optional
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from contextlib import asynccontextmanager

# 在导入其他模块之前设置 multiprocessing 启动方法
# 使用 spawn 模式确保跨平台兼容性
try:
    multiprocessing.set_start_method('spawn', force=True)
except RuntimeError:
    pass  # 已经设置过了

# 添加项目根目录到 Python 路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.state_storage import StateStorage
from api.websocket_manager import WebSocketManager
from api.state_extractor import StateExtractor
from api.broadcast_queue import BroadcastQueue
from api.input_buffer import InputBuffer


# 全局管理器
websocket_manager = WebSocketManager()
running_tasks: Dict[str, multiprocessing.Process] = {}

# 延迟初始化的全局变量
_manager = None
broadcast_queue = None
input_buffer = None


def init_manager():
    """初始化 Manager 和队列（在 main 中调用）"""
    global _manager, broadcast_queue, input_buffer
    if _manager is None:
        _manager = multiprocessing.Manager()
        broadcast_queue = BroadcastQueue(manager=_manager)
        input_buffer = InputBuffer(manager=_manager)


def run_automas_task(task_id: str, query: str, task_dir: str, debug: bool,
                     broadcast_q, input_q, register_q):
    """
    在子进程中运行 automas 任务

    Args:
        task_id: 任务ID
        query: 用户查询
        task_dir: 任务目录
        debug: 是否开启调试模式
        broadcast_q: 广播队列（用于状态推送）
        input_q: 输入队列（用于用户输入）
        register_q: 注册队列（用于子进程注册 query）
    """
    import sys

    # 设置 sys.argv 供 app.py 的 argparse 使用
    # app.py 期望的参数: --query, --task_dir, --task_id, --debug, --dry_run
    sys.argv = [
        "app.py",
        "--query", query,
        "--task_dir", task_dir,
        "--task_id", task_id,
        "--dry_run"  # 始终使用 dry_run 模式（不发送 observe）
    ]
    if debug:
        sys.argv.append("--debug")

    # 设置环境变量（供 app.py 使用）
    os.environ["AUTOMAS_WEB_MODE"] = "1"
    os.environ["AUTOMAS_TASK_ID"] = task_id
    os.environ["AUTOMAS_TASK_DIR"] = task_dir
    if debug:
        os.environ["IS_DEBUG_ENABLED"] = "1"
    else:
        os.environ["IS_DEBUG_ENABLED"] = "0"

    # 设置队列到全局（供 StatePusher 和 InputBuffer 使用）
    from api.broadcast_queue import set_queue
    from api.input_buffer import set_queues
    set_queue(broadcast_q)
    set_queues(input_q, register_q)
    print(f"[run_automas_task] Queues set: broadcast_q={broadcast_q}, input_q={input_q}, register_q={register_q}")

    # 导入并运行 app
    import app as automas_app
    automas_app.main()


async def broadcast_consumer():
    """
    广播消费者
    从 BroadcastQueue 读取状态更新并推送给 WebSocket 客户端
    同时在主进程中保存状态到 StateStorage
    """
    loop = asyncio.get_event_loop()
    while True:
        try:
            # 从队列获取消息（在 executor 中运行避免阻塞）
            msg = await loop.run_in_executor(None, broadcast_queue.get, 0.1)

            if msg:
                task_id = msg.get("task_id")
                message = msg.get("message")

                if task_id and message:
                    print(f"[BroadcastConsumer] Broadcasting state for task {task_id}")
                    
                    # 在主进程中保存状态到 StateStorage
                    # 这样 monitor_tasks 可以获取到完整状态
                    StateStorage.save(task_id, message)
                    
                    # 广播给该任务的所有 WebSocket 连接
                    await websocket_manager.broadcast(task_id, message)

        except Exception as e:
            # 队列为空或出错，短暂休眠
            await asyncio.sleep(0.01)


async def monitor_tasks():
    """定期监控任务状态，清理已完成的任务"""
    while True:
        await asyncio.sleep(5)  # 每5秒检查一次

        completed_tasks = []
        for task_id, process in list(running_tasks.items()):
            # 检查进程是否已经结束
            if not process.is_alive():
                # 进程已结束
                completed_tasks.append(task_id)
                exit_code = process.exitcode
                print(f"Task {task_id} completed with exit code: {exit_code}")

                # 保存最终状态到文件
                final_state = StateStorage.get(task_id)
                if final_state:
                    # 调试：打印 final_state 的键
                    print(f"[DEBUG] Final state keys: {list(final_state.keys()) if isinstance(final_state, dict) else 'Not a dict'}")
                    print(f"[DEBUG] Final state summary_body: {repr(final_state.get('summary_body', 'NOT_FOUND'))}")
                    
                    # 检查是否真正完成（summary_body 有值）
                    summary_body = final_state.get("summary_body", "")
                    is_really_completed = bool(summary_body and str(summary_body).strip())

                    if is_really_completed:
                        print(f"Task {task_id} fully completed (with summary)")
                    else:
                        print(f"Task {task_id} process ended but summary not generated yet")

                    StateStorage.mark_task_completed(task_id, final_state)
                else:
                    # 如果没有状态，也标记为完成（记录基本信息）
                    print(f"Task {task_id} completed but no state found")
                    StateStorage.mark_task_completed(task_id, {"task_id": task_id, "status": "completed", "summary_body": ""})

        # 从 running_tasks 中移除已完成的任务
        for task_id in completed_tasks:
            running_tasks.pop(task_id, None)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时：启动监控任务与广播消费者
    monitor_task = asyncio.create_task(monitor_tasks())
    broadcast_task = asyncio.create_task(broadcast_consumer())
    yield
    # 关闭时：取消所有任务
    monitor_task.cancel()
    broadcast_task.cancel()
    try:
        await monitor_task
    except asyncio.CancelledError:
        pass
    try:
        await broadcast_task
    except asyncio.CancelledError:
        pass


app = FastAPI(title="Automas Web API", version="1.0.0", lifespan=lifespan)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 请求模型
class CreateTaskRequest(BaseModel):
    query: str


class UserInputRequest(BaseModel):
    response: str


@app.post("/api/tasks")
def create_task(request: CreateTaskRequest):
    """
    创建新任务，启动 automas 进程
    """
    global broadcast_queue, input_buffer
    
    task_id = str(uuid.uuid4())[:8]
    task_dir = f"web_{task_id}"

    # 调试输出
    print(f"[Server] Starting task {task_id}")
    print(f"  Query: {request.query}")
    print(f"  Task Dir: {task_dir}")

    # 获取队列（Manager 创建的队列可以直接传递给子进程）
    broadcast_q = broadcast_queue.get_queue()
    input_q = input_buffer.get_submit_queue()
    register_q = input_buffer.get_register_queue()

    # 判断是否开启调试模式
    debug = os.environ.get("IS_DEBUG_ENABLED") == "1"

    # 启动 automas 进程
    try:
        process = multiprocessing.Process(
            target=run_automas_task,
            args=(task_id, request.query, task_dir, debug, broadcast_q, input_q, register_q)
        )
        process.start()
        running_tasks[task_id] = process
        return {"task_id": task_id, "status": "created", "message": "任务已创建并开始执行"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start task: {str(e)}")


@app.get("/api/tasks/{task_id}/state")
def get_task_state(task_id: str):
    """
    获取任务状态 - 先从内存查，再从文件查
    """
    state = StateStorage.get(task_id)
    if not state:
        raise HTTPException(status_code=404, detail="Task not found")

    # 添加任务完成状态信息
    is_completed = StateStorage.is_task_completed(task_id)
    is_really_completed = StateStorage.is_task_really_completed(task_id)
    process = running_tasks.get(task_id)
    is_running = process is not None and process.is_alive()
    waiting_for_input = input_buffer.has_pending(task_id)
    return {
        "task_id": task_id,
        "is_running": is_running,
        "is_completed": is_completed,
        "is_really_completed": is_really_completed,
        "waiting_for_input": waiting_for_input,
        "state": state
    }


@app.post("/api/tasks/{task_id}/input")
def submit_input(task_id: str, request: UserInputRequest):
    """
    用户提交响应
    """
    success = input_buffer.submit_response(task_id, request.response)
    if not success:
        raise HTTPException(status_code=400, detail="No pending query waiting for response")

    return {"success": True, "message": "输入已接收，任务继续执行"}


@app.get("/api/tasks/{task_id}/status")
def get_task_status(task_id: str):
    """
    获取任务状态（简化版）
    """
    process = running_tasks.get(task_id)
    is_running = process is not None and process.is_alive()

    # 检查是否有等待中的问题
    waiting_for_input = input_buffer.has_pending(task_id)

    # 检查任务完成状态
    is_completed = StateStorage.is_task_completed(task_id)
    is_really_completed = StateStorage.is_task_really_completed(task_id)

    return {
        "task_id": task_id,
        "is_running": is_running,
        "is_completed": is_completed,
        "is_really_completed": is_really_completed,
        "waiting_for_input": waiting_for_input,
    }


@app.websocket("/ws/{task_id}")
async def websocket_endpoint(websocket: WebSocket, task_id: str):
    """
    WebSocket 连接端点
    """
    await websocket_manager.connect(websocket, task_id)
    try:
        while True:
            # 接收客户端消息（用于心跳检测或其他用途）
            data = await websocket.receive_json()

            if data.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
            elif data.get("type") == "get_state":
                # 客户端请求当前状态
                state = StateStorage.get(task_id)
                if state:
                    await websocket.send_json(state)  # 直接传回状态

    except WebSocketDisconnect:
        websocket_manager.disconnect(websocket, task_id)
    except Exception as e:
        print(f"WebSocket error: {e}")
        websocket_manager.disconnect(websocket, task_id)


@app.delete("/api/tasks/{task_id}")
def stop_task(task_id: str):
    """
    停止任务
    """
    process = running_tasks.get(task_id)
    if process and process.is_alive():
        process.terminate()
        process.join(timeout=5)
        if process.is_alive():
            process.kill()

        # 清理资源
        running_tasks.pop(task_id, None)
        StateStorage.delete(task_id)

        return {"task_id": task_id, "status": "terminated"}

    return {"task_id": task_id, "status": "not_running"}


@app.get("/api/tasks")
def list_tasks():
    """
    获取所有任务列表
    """
    task_ids = StateStorage.get_all_task_ids()
    tasks = []

    for task_id in task_ids:
        state = StateStorage.get(task_id)
        if state:
            tasks.append({
                "task_id": task_id,
                "overall_goal": state.get("plan_body", {}).get("overall_goal", ""),
                "is_mission_accomplished": state.get("plan_body", {}).get("is_mission_accomplished", False)
            })

    return {"tasks": tasks}


if __name__ == "__main__":
    import uvicorn
    
    # 在 main 中初始化 Manager（避免 spawn 模式下的问题）
    init_manager()
    
    uvicorn.run(app, host="0.0.0.0", port=8000)
