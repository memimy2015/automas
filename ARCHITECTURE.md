# Automas Web 服务架构文档

## 1. 系统概述

Automas Web 服务是一个基于 FastAPI 的 Web 服务，用于将原有的命令行多 Agent 系统改造为可通过 Web API 和 WebSocket 访问的服务。

### 核心特性
- HTTP API 用于任务管理和用户输入
- WebSocket 用于实时状态推送
- 跨进程通信支持（server.py 主进程 + app.py 子进程）
- 使用 multiprocessing.Manager().Queue() 实现高效 IPC

---

## 2. 架构设计

### 2.1 进程结构

```
┌─────────────────────────────────────────────────────────────┐
│                        server.py (主进程)                    │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │  FastAPI App │  │ WebSocket Mgr│  │ Broadcast Consumer│  │
│  └──────────────┘  └──────────────┘  └──────────────────┘  │
│         │                 │                      │          │
│         ▼                 ▼                      ▼          │
│  ┌─────────────────────────────────────────────────────┐   │
│  │      multiprocessing.Manager().Queue() IPC           │   │
│  │  ┌─────────────────┐      ┌─────────────────┐      │   │
│  │  │  broadcast_queue │      │  input_queue    │      │   │
│  │  │  (状态推送)       │      │  (用户输入)      │      │   │
│  │  └─────────────────┘      └─────────────────┘      │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                              │
                              │ multiprocessing.Process
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      app.py (子进程)                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │ContextManager│  │   Notifier   │  │   StatePusher    │  │
│  └──────────────┘  └──────────────┘  └──────────────────┘  │
│         │                 │                      │          │
│         ▼                 ▼                      ▼          │
│  ┌─────────────────────────────────────────────────────┐   │
│  │      multiprocessing.Manager().Queue() IPC           │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

**关键说明**:
- `server.py` 和 `app.py` 是通过 `multiprocessing.Process` 启动的独立进程
- 进程间通过 `multiprocessing.Manager().Queue()` 进行通信
- 队列由 Manager 创建，可以在 Windows spawn 模式下正确传递给子进程
- 每个任务对应一个独立的 `app.py` 子进程

---

## 2.2 跨进程通信机制

使用 `multiprocessing.Manager().Queue()` 实现高效的进程间通信：

**为什么选择 Manager().Queue()？**

在 Windows 上使用 spawn 启动方法时，直接使用 `multiprocessing.Queue()` 会遇到问题：
1. spawn 模式会重新导入主模块
2. Queue 对象无法通过 pickle 正确序列化传递
3. 导致子进程无法访问父进程创建的队列

`multiprocessing.Manager()` 创建一个 server 进程来管理共享对象，队列通过代理对象访问，可以在 spawn 模式下正确工作。

### 2.2.1 BroadcastQueue（状态更新通知）

**文件**: `api/broadcast_queue.py`

**机制**:
```
主进程 (server.py)
    ↓ 创建 Manager
manager = multiprocessing.Manager()
    ↓ 创建 Queue
broadcast_queue = BroadcastQueue(manager=manager)
    ↓ 传递给子进程
Process(target=run_automas_task, args=(..., broadcast_q, ...))

子进程 (app.py)
    ↓ StatePusher.push()
broadcast_queue.put({"task_id": ..., "message": ...})
    ↓

主进程 (broadcast_consumer)
    ↓ 读取队列
msg = broadcast_queue.get(timeout=0.1)
    ↓ WebSocket 广播
websocket_manager.broadcast(task_id, message)
```

**关键方法**:
- `get_queue()`: 获取队列对象（用于传递给子进程）
- `put(task_id, message)`: 子进程调用，放入状态消息
- `get(timeout)`: 主进程调用，读取状态消息
- `set_queue(queue)`: 子进程中设置全局队列

### 2.2.2 InputBuffer（用户输入传递）

**文件**: `api/input_buffer.py`

**机制**:
```
主进程 (server.py)
    ↓ 创建 Manager
manager = multiprocessing.Manager()
    ↓ 创建两个 Queue
input_buffer = InputBuffer(manager=manager)
    - _submit_queue: 用户响应传递（server写入，子进程读取）
    - _register_queue: query注册通知（子进程写入，server读取）
    ↓ 传递给子进程

子进程 (Agent 调用 call_user)
    ↓ register_query() [全局函数]
_register_queue.put({"task_id": ..., "query": ...})
    ↓
    │
主进程 (InputBuffer._register_consumer 线程)
    ↓ 读取 _register_queue
更新 _pending_queries[task_id] = query
    │
    ↓ 用户提交输入
主进程 (submit_response)
检查 _pending_queries，然后 _submit_queue.put()
    ↑
    │
子进程 (wait_for_response)
轮询 _submit_queue.get(timeout=0.1)
```

**关键方法**:
- `get_submit_queue()`: 获取提交队列（传递给子进程）
- `get_register_queue()`: 获取注册队列（传递给子进程）
- `register_query(task_id, query)`: 在主进程中直接注册等待输入的问题
- `submit_response(task_id, response)`: Web API 接收用户响应，检查 pending 后写入队列
- `wait_for_response(task_id, timeout)`: 全局函数，Agent 阻塞等待响应（轮询队列）
- `set_queues(submit_queue, register_queue)`: 子进程中设置全局队列（两个队列）

**重要设计**:
- 使用两个 Queue 实现双向通信
- `_pending_queries` 字典只在主进程中维护（通过消费者线程更新）
- 子进程通过 `_register_queue` 发送注册请求，避免跨进程共享状态的问题

### 2.2.3 StateStorage（状态持久化）

**文件**: `api/state_storage.py`

**机制**:
- 内存缓存: `_states` 字典（task_id → state）
- 文件存储: `storage/tasks/completed/{task_id}.json`
- 任务索引: `storage/tasks/completed/index.json`

**关键方法**:
- `save(task_id, state)`: 保存到内存（深拷贝）
- `get(task_id)`: 先查内存，再查文件
- `mark_task_completed(task_id, final_state)`: 标记完成并持久化

---

## 2.3 状态流转

```
┌─────────────┐     POST /api/tasks      ┌─────────────┐
│   客户端     │ ───────────────────────> │   server    │
│  (Web/测试)  │                          │             │
└─────────────┘                          └──────┬──────┘
     ▲                                          │
     │                                          │ Process.start()
     │                                          ▼
     │                                   ┌─────────────┐
     │                                   │   app.py    │
     │                                   │  (子进程)    │
     │                                   └──────┬──────┘
     │                                          │
     │         ┌────────────────────────────────┤
     │         │                                │
     │    WebSocket                    StatePusher
     │    状态推送                      (触发点)
     │         │                                │
     │         ▼                                ▼
     │  ┌─────────────┐              ┌─────────────────┐
     └──┤  状态更新    │ <─────────── │ 1. StateStorage │
        │  (JSON)     │              │ 2. broadcast_queue│
        └─────────────┘              └─────────────────┘
                                          │
                                          ▼
                                    ┌─────────────┐
                                    │Manager.Queue│
                                    └─────────────┘

需要用户输入时:

┌─────────┐     register_query()     ┌─────────────────┐
│  Agent  │ ───────────────────────> │ 全局函数(子进程)  │
└────┬────┘                          └────────┬────────┘
     │                                        │
     │ _register_queue.put()                   │
     │                                        │
     │                               ┌────────▼────────┐
     │                               │ _register_queue │
     │                               │ (Manager.Queue) │
     │                               └────────┬────────┘
     │                                        │
     │                               ┌────────▼────────┐
     │                               │ 主进程消费者线程 │
     │                               │ _pending_queries│
     │                               └────────┬────────┘
     │                                        │
     │ wait_for_response()                   │ submit_response()
     │ (轮询 _submit_queue)                    │ 检查 pending
     │                                        │ 然后写入队列
     │                               ┌────────▼────────┐
     │                               │ _submit_queue   │
     │                               │ (Manager.Queue) │
     │                               └────────┬────────┘
     │                                        │
     │ <──────────────────────────────────────┤
     │      从 _submit_queue 读取响应          │
     │                                        │
     ▼                                        ▼
┌─────────┐                            ┌─────────────┐
│ 继续执行  │                            │  用户输入    │
└─────────┘                            │  (HTTP API)  │
                                       └─────────────┘
```

---

## 3. 核心组件

### 3.1 server.py（FastAPI 服务）

**文件**: `api/server.py`

**功能**:
- HTTP API 端点（创建任务、提交输入、查询状态）
- WebSocket 连接管理
- 后台任务（广播消费者、任务监控）
- 使用 `multiprocessing.Process` 启动子进程

**后台任务**:
1. `broadcast_consumer()`: 从 BroadcastQueue 读取状态并 WebSocket 广播
2. `input_consumer()`: 处理输入队列中的响应
3. `monitor_tasks()`: 监控子进程状态，清理已完成任务

**关键端点**:
- `POST /api/tasks`: 创建任务，启动 app.py 子进程
- `POST /api/tasks/{task_id}/input`: 用户提交输入
- `GET /api/tasks/{task_id}/state`: 查询任务状态
- `WebSocket /ws/{task_id}`: 实时状态推送

**子进程启动**:
```python
# 创建 Manager 实例
_manager = multiprocessing.Manager()

# 使用 Manager 创建队列
broadcast_queue = BroadcastQueue(manager=_manager)
input_buffer = InputBuffer(manager=_manager)

def run_automas_task(task_id, query, task_dir, debug, broadcast_q, input_q, register_q):
    # 设置环境变量
    os.environ["AUTOMAS_WEB_MODE"] = "1"
    # 设置队列
    set_queue(broadcast_q)
    set_queues(input_q, register_q)  # 设置两个队列
    # 运行 app
    import app as automas_app
    automas_app.main()

# 获取队列
broadcast_q = broadcast_queue.get_queue()
input_q = input_buffer.get_submit_queue()
register_q = input_buffer.get_register_queue()

process = multiprocessing.Process(
    target=run_automas_task,
    args=(task_id, query, task_dir, debug, broadcast_q, input_q, register_q)
)
process.start()
```

### 3.2 StatePusher（状态推送触发器）

**文件**: `api/state_pusher.py`

**功能**: 在关键节点提取 ContextManager 状态并推送到 BroadcastQueue

**触发点**:

| 触发原因 | 说明 | 代码位置 |
|---------|------|---------|
| `task_started` | 任务开始执行时 | `app.py` |
| `call_user` | Agent/Planner/Claimer/Summarizer 调用用户输入时 | `notifier.py` |
| `update_progress` | Agent 使用 update_progress 工具更新里程碑时 | `context_manager.py` |
| `agent_created` | AgentFactory 成功创建子智能体时 | `context_manager.py` |
| `agent_completed` | Agent 执行完成并提交结果时 | `context_manager.py` |
| `claimer_completed` | Claimer 执行完成时 | `ClaimerAgent.py` |
| `planner_completed` | Planner 执行完成时 | `PlannerAgent.py` |
| `summarizer_completed` | Summarizer 执行完成时 | `SummarizerAgent.py` |
| `task_completed` | 整个任务全部完成时（Summarizer 生成总结后） | `app.py` |

**注意**: 只在 Web 模式下启用（通过 `AUTOMAS_WEB_MODE` 环境变量判断）

### 3.3 StateExtractor（状态提取器）

**文件**: `api/state_extractor.py`

**功能**: 从 ContextManager 提取状态并格式化为指定 JSON 结构

**输出格式**:
```json
{
  "task_id": "...",
  "chat_body": [...],
  "plan_body": {...},
  "current_subagent": {...},
  "summary_body": "..."
}
```

### 3.4 WebSocketManager（WebSocket 管理）

**文件**: `api/websocket_manager.py`

**功能**: 管理 WebSocket 连接，支持按 task_id 广播

**关键方法**:
- `connect(websocket, task_id)`: 连接并关联到任务
- `disconnect(websocket, task_id)`: 断开连接
- `broadcast(task_id, message)`: 向指定任务的所有客户端广播

---

## 4. 环境变量

| 变量名 | 说明 | 设置位置 |
|--------|------|----------|
| `AUTOMAS_WEB_MODE` | 启用 Web 模式（1=启用） | server.py → app.py |
| `AUTOMAS_TASK_ID` | 任务 ID | server.py → app.py |
| `AUTOMAS_TASK_DIR` | 任务目录 | server.py → app.py |
| `IS_DEBUG_ENABLED` | 调试模式（1=启用） | 命令行 --debug |

---

## 5. 启动流程

### 5.1 启动服务

```bash
cd api
python server.py
```

或:

```bash
uvicorn api.server:app --host 0.0.0.0 --port 8000
```

### 5.2 创建任务流程

1. 客户端 `POST /api/tasks` 提交查询
2. server 生成 task_id
3. server 创建 `multiprocessing.Manager()` 实例
4. server 使用 Manager 创建 Queue 对象
5. server 启动 `multiprocessing.Process`，传递队列参数
6. app.py 子进程启动，通过 `set_queue()` 设置全局队列
7. server 返回 task_id 给客户端
8. 客户端连接 WebSocket `/ws/{task_id}`
9. app.py 执行过程中触发 StatePusher，状态通过 Queue 传递
10. server 的 broadcast_consumer 读取并 WebSocket 推送

---

## 6. 测试工具

**文件**: `test_websocket.py`

**功能**: 完整的 WebSocket 测试客户端

**使用**:
```bash
python test_websocket.py --query "你的问题"
```

**流程**:
1. 创建任务
2. 连接 WebSocket
3. 接收状态更新
4. 检测需要输入时提示用户
5. 提交用户输入
6. 等待任务完成

---

## 7. 关键注意事项

### 7.1 进程隔离
- `server.py` 和 `app.py` 是独立的进程
- 内存不共享，必须通过 Queue 通信
- 每个任务对应一个独立的子进程

### 7.2 Manager().Queue() 的优势
- 支持 Windows spawn 启动方法
- 无需轮询，阻塞/超时读取
- 无需清理临时文件
- 比文件系统 IPC 更高效

### 7.3 Windows 平台注意事项
- 必须使用 `multiprocessing.set_start_method('spawn')`
- 子进程代码需要放在 `if __name__ == "__main__":` 保护下
- 必须使用 `multiprocessing.Manager()` 创建队列
- 队列对象通过参数传递给子进程

### 7.4 任务生命周期

```
任务执行流程:

1. 任务启动
   ↓
2. Claimer 执行（需求澄清）
   ↓
3. Planner 执行（计划制定）
   ↓
4. 循环执行 Agent 任务
   - Agent 创建
   - Agent 执行
   - 可能调用用户输入 (call_user)
   - 提交结果
   ↓
5. 所有子任务完成 (is_accomplished = true)
   ↓
6. Summarizer 执行（生成总结）← 此时进程仍在运行
   ↓
7. 进程结束
   ↓
8. 状态保存到文件
```

**重要说明**:
- `is_completed`: 进程已结束（步骤7后）
- `is_really_completed`: summarizer 已生成总结（summary_body 非空）
- 在步骤6期间，任务进程仍在运行，客户端应等待 `task_completed` 状态推送

### 7.5 与 multiprocessing.Queue() 的区别

| 特性 | multiprocessing.Queue() | multiprocessing.Manager().Queue() |
|------|------------------------|----------------------------------|
| Windows spawn 支持 | ❌ 不支持 | ✅ 支持 |
| 传递方式 | 通过参数传递（会失败） | 通过代理对象传递 |
| 实现机制 | 直接共享内存 | 通过 Manager server 进程 |
| 性能 | 更高 | 稍低（有序列化开销） |
| 适用场景 | Unix fork | Windows spawn |

---

## 8. 文件清单

| 文件 | 说明 |
|------|------|
| `api/server.py` | FastAPI 服务主文件（Manager-based 版本） |
| `api/broadcast_queue.py` | 基于 Manager.Queue 的广播队列 |
| `api/input_buffer.py` | 基于 Manager.Queue 的输入缓冲 |
| `api/state_storage.py` | 状态存储（内存+文件） |
| `api/state_extractor.py` | 状态提取器 |
| `api/state_pusher.py` | 状态推送触发器 |
| `api/websocket_manager.py` | WebSocket 连接管理 |
| `test_websocket.py` | WebSocket 测试客户端 |
