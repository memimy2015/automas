# Automas Web API 使用文档

本文档描述了 Automas 多智能体系统的 Web API 接口，用于将命令行交互转换为 Web 服务。

## 概述

Automas Web API 提供了以下功能：
- 创建任务并启动多智能体执行流程
- 实时获取任务状态（计划、对话历史、当前执行智能体、总结）
- 通过 WebSocket 接收实时状态推送
- 提交用户输入以继续任务执行
- 任务完成后状态持久化存储

## 启动服务

```bash
# 推荐方式：直接运行 server.py（会正确初始化 Windows spawn 所需的 Manager/Queue）
python api/server.py

# 可选方式：以模块方式启动（等价于直接运行 server.py）
python -m api.server
```

服务默认在 `http://localhost:8000` 启动。

## API 端点

### 1. 创建任务

**POST** `/api/tasks`

创建新任务并启动执行流程。

**请求体：**
```json
{
  "query": "生成一份关于AI发展趋势的PPT"
}
```

**响应：**
```json
{
  "task_id": "a1b2c3d4",
  "status": "created",
  "message": "任务已创建并开始执行"
}
```

### 2. 获取任务状态

**GET** `/api/tasks/{task_id}/state`

获取指定任务的完整状态信息。支持从内存或文件系统加载（任务完成后会自动保存到文件）。

**响应：**
```json
{
  "task_id": "a1b2c3d4",
  "is_running": false,
  "is_completed": true,
  "is_really_completed": true,
  "state": {
    "task_id": "a1b2c3d4",
    "chat_body": [
      {
        "role": "user",
        "content": "生成一份关于AI发展趋势的PPT"
      },
      {
        "role": "规划者",
        "content": "我将为您规划这个任务..."
      },
      {
        "role": "澄清者",
        "content": "请问PPT需要包含哪些具体内容？"
      }
    ],
    "plan_body": {
      "...": "（此处为任务计划结构，详见“数据结构说明”）"
    },
    "current_subagent": {
      "...": "（此处为当前子智能体信息，详见“数据结构说明”）"
    },
    "summary_body": "任务已完成，成功生成AI发展趋势PPT..."
  }
}
```

**字段说明：**
- `is_running`: 任务是否正在运行
- `is_completed`: 任务进程是否已结束（已保存到文件系统）
- `is_really_completed`: 任务是否真正完成（summarizer 已生成总结，summary_body 非空）
- `state`: 完整的任务状态数据

**注意：** `is_completed` 表示进程已结束，但 `is_really_completed` 表示 summarizer 已生成总结。在 summarizer 运行期间，`is_completed` 可能为 true 但 `is_really_completed` 为 false。

### 3. 获取任务运行状态（简化版）

**GET** `/api/tasks/{task_id}/status`

获取任务的简要运行状态，包括是否运行中、是否等待用户输入等。

**响应：**
```json
{
  "task_id": "a1b2c3d4",
  "is_running": true,
  "is_completed": false,
  "is_really_completed": false,
  "waiting_for_input": true,
  "pending_query": "请问PPT需要包含哪些具体内容？"
}
```

### 4. 提交用户输入

**POST** `/api/tasks/{task_id}/input`

当系统需要用户输入时（如澄清问题），通过此接口提交回答。

**请求体：**
```json
{
  "response": "PPT需要包含机器学习、深度学习、大语言模型三个部分"
}
```

**响应：**
```json
{
  "success": true,
  "message": "输入已接收，任务继续执行"
}
```

### 5. 停止任务

**DELETE** `/api/tasks/{task_id}`

强制停止正在运行的任务。

**响应：**
```json
{
  "task_id": "a1b2c3d4",
  "status": "terminated"
}
```

### 6. 获取所有任务列表

**GET** `/api/tasks`

获取所有任务（包括运行中和已完成的）列表。

**响应：**
```json
{
  "tasks": [
    {
      "task_id": "a1b2c3d4",
      "overall_goal": "生成AI发展趋势PPT",
      "is_mission_accomplished": true
    }
  ]
}
```

### 7. WebSocket 实时通信

**WS** `/ws/{task_id}`

建立 WebSocket 连接以接收实时状态更新。

**连接示例（JavaScript）：**
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/a1b2c3d4');

ws.onopen = () => {
  console.log('WebSocket 连接已建立');
};

ws.onmessage = (event) => {
  const state = JSON.parse(event.data);
  console.log('收到状态更新:', state);
  // 直接用 state 更新 UI 显示（state 即 {task_id, chat_body, plan_body, current_subagent, summary_body}）
};

ws.onclose = () => {
  console.log('WebSocket 连接已关闭');
};
```

**推送的消息格式：**
```json
{
  "task_id": "a1b2c3d4",
  "chat_body": [...],
  "plan_body": {...},
  "current_subagent": {...},
  "summary_body": "..."
}
```

**说明：** WebSocket 推送的消息直接是状态数据（不包含 `is_running/is_completed` 这些包装字段）。任务运行状态/是否等待输入请使用 `GET /api/tasks/{task_id}/status` 查询。

**客户端请求消息：**
```javascript
// 心跳检测
{ "type": "ping" }

// 请求当前状态
{ "type": "get_state" }
```

## 状态推送触发时机

系统会在以下时机自动推送状态更新：

### 任务生命周期触发点

| 触发原因 | 说明 | 代码位置 |
|---------|------|---------|
| `task_started` | 任务开始执行时 | `app.py` |
| `task_completed` | 整个任务全部完成时（Summarizer 生成总结后） | `app.py` |

### Agent 相关触发点

| 触发原因 | 说明 | 代码位置 |
|---------|------|---------|
| `agent_created` | AgentFactory 成功创建子智能体时 | `context_manager.py` |
| `agent_completed` | Agent 执行完成并提交结果时（包括成功、失败、取消） | `context_manager.py` |
| `claimer_completed` | Claimer 执行完成时 | `ClaimerAgent.py` |
| `planner_completed` | Planner 执行完成时 | `PlannerAgent.py` |
| `summarizer_completed` | Summarizer 执行完成时 | `SummarizerAgent.py` |

### 用户交互触发点

| 触发原因 | 说明 | 代码位置 |
|---------|------|---------|
| `call_user` | 系统需要用户输入时（Planner、Claimer、Summarizer、Agent 都可能触发） | `notifier.py` |

### 进度更新触发点

| 触发原因 | 说明 | 代码位置 |
|---------|------|---------|
| `update_progress` | Agent 使用 update_progress 工具更新里程碑时 | `context_manager.py` |

### 触发时机详解

1. **task_started**: 网页模式下初始化 StatePusher 后立即推送，通知客户端任务已开始

2. **agent_created**: AgentFactory 创建子 Agent 成功后触发，此时 `current_subagent` 会更新为新创建的 Agent

3. **call_user**: 当系统需要用户输入时触发（如澄清问题、确认计划等），此时客户端应显示输入框

4. **update_progress**: Agent 调用 update_progress 工具时触发，更新 plan_body 中对应里程碑的状态

5. **agent_completed**: Agent 执行完成并调用 submit_sub_objective 后触发，表示当前子目标已完成

6. **claimer/planner/summarizer_completed**: 特殊 Agent 完成时触发，表示对应阶段结束

7. **task_completed**: 主循环结束、Summarizer 生成总结后触发，表示整个任务完成

## 任务状态持久化

### 自动保存机制

- 任务运行期间：状态保存在内存中，支持实时查询
- 任务完成后（进程结束）：状态自动保存到文件系统
- 服务重启后：可以从文件系统加载已完成的任务状态

### 存储路径

```
storage/
└── tasks/
    └── completed/
        ├── index.json              # 已完成任务ID索引
        ├── {task_id_1}.json        # 任务1的最终状态
        ├── {task_id_2}.json        # 任务2的最终状态
        └── ...
```

### 状态查询流程

1. **查询任务状态** `GET /api/tasks/{task_id}/state`：
   - 先检查内存中的运行中任务
   - 如果不在内存中，自动从文件系统加载
   - 返回 `is_running` 和 `is_completed` 标识任务状态

2. **定期监控**：
   - 服务每5秒检查一次运行中的任务进程
   - 进程结束后自动保存状态到文件
   - 从 `running_tasks` 中移除已完成的任务

## 前端交互流程

### 基本流程

```
1. 用户输入问题
   ↓
2. 前端调用 POST /api/tasks 创建任务
   ↓
3. 建立 WebSocket 连接 /ws/{task_id}
   ↓
4. 接收状态更新，渲染到界面
   ↓
5. 如果 `GET /api/tasks/{task_id}/status` 显示 `waiting_for_input=true`
   ↓
6. 显示输入框，用户输入后调用 POST /api/tasks/{task_id}/input
   ↓
7. 继续接收状态更新...
   ↓
8. 任务完成（通过 is_running=false 和 is_completed=true 判断）
   ↓
9. 可以从文件系统重新加载历史任务状态
```

### 示例代码

```javascript
class AutomasClient {
  constructor(baseUrl = 'http://localhost:8000') {
    this.baseUrl = baseUrl;
    this.ws = null;
  }

  // 创建任务
  async createTask(query) {
    const response = await fetch(`${this.baseUrl}/api/tasks`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query })
    });
    return response.json();
  }

  // 获取状态（支持运行中和已完成的任务）
  async getState(taskId) {
    const response = await fetch(`${this.baseUrl}/api/tasks/${taskId}/state`);
    return response.json();
  }

  // 获取简要状态
  async getStatus(taskId) {
    const response = await fetch(`${this.baseUrl}/api/tasks/${taskId}/status`);
    return response.json();
  }

  // 提交用户输入
  async submitInput(taskId, response) {
    const res = await fetch(`${this.baseUrl}/api/tasks/${taskId}/input`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ response })
    });
    return res.json();
  }

  // 停止任务
  async stopTask(taskId) {
    const res = await fetch(`${this.baseUrl}/api/tasks/${taskId}`, {
      method: 'DELETE'
    });
    return res.json();
  }

  // 获取所有任务
  async listTasks() {
    const res = await fetch(`${this.baseUrl}/api/tasks`);
    return res.json();
  }

  // 连接 WebSocket
  connectWebSocket(taskId, onMessage) {
    this.ws = new WebSocket(`ws://localhost:8000/ws/${taskId}`);
    this.ws.onmessage = (event) => {
      const state = JSON.parse(event.data);
      onMessage(state);
    };
    return this.ws;
  }
}

// 使用示例
const client = new AutomasClient();

async function startTask() {
  // 1. 创建任务
  const { task_id } = await client.createTask('生成一份周报PPT');
  
  // 2. 连接 WebSocket
  client.connectWebSocket(task_id, async (state) => {
    console.log('状态更新:', state);
    updateUI(state);

    const status = await client.getStatus(task_id);
    if (status.waiting_for_input) {
      showInputDialog(status.pending_query);
    }
    if (status.is_completed) {
      console.log('任务进程已结束');
    }
  });
}

async function submitUserResponse(taskId, response) {
  await client.submitInput(taskId, response);
}

// 加载历史任务
async function loadHistoricalTask(taskId) {
  const data = await client.getState(taskId);
  if (data.is_completed) {
    console.log('加载历史任务:', data.state);
    updateUI(data.state);
  }
}
```

## 数据结构说明

### chat_body

对话历史数组，包含用户和各个智能体的消息。

角色名称根据消息内容前缀自动识别：
- `规划者:` → role: "规划者"
- `澄清者:` → role: "澄清者"
- `总结者:` → role: "总结者"
- `{role_name}:` → role: 对应智能体名称

### plan_body

任务计划结构来自 `ContextManager.task_state` 的抽取结果，包含 `tasks/next_step/is_mission_accomplished/overall_goal` 等字段，具体字段以接口返回为准。

### current_subagent

当前正在执行的子智能体信息来自 `latest_agent_factory_output` 与当前 step 的 milestones 抽取结果，具体字段以接口返回为准。

### summary_body

任务整体总结文本，由 Summarizer 生成。

## 命令行兼容性

**重要：** 修改后的代码完全兼容原有的命令行执行方式。

### 命令行模式

当不设置环境变量 `AUTOMAS_WEB_MODE` 时，系统以命令行模式运行：

```bash
python app.py
```

行为与之前完全一致：
- 从标准输入读取用户输入
- 输出到标准输出
- 不启动 Web 服务

### Web 模式

设置环境变量后，系统以 Web 模式运行：

```bash
# Windows
set AUTOMAS_WEB_MODE=1
python api/server.py

# Linux/Mac
export AUTOMAS_WEB_MODE=1
python api/server.py
```

### 调试模式

添加 `--debug` 参数开启调试模式（启用 dump 功能）：

```bash
# 命令行模式
python app.py --query "生成PPT" --debug

# Web 模式（设置环境变量）
set IS_DEBUG_ENABLED=1
python api/server.py
```

### 混合模式

当前实现要求先初始化 `multiprocessing.Manager()` 及其队列（用于 Windows spawn 下跨进程通信）。因此建议使用下列任一方式启动：

```bash
python api/server.py
python -m api.server
```

## 错误处理

### HTTP 错误码

| 状态码 | 说明 |
|-------|------|
| 200 | 请求成功 |
| 404 | 任务不存在 |
| 422 | 请求参数错误 |
| 500 | 服务器内部错误 |

### 错误响应格式

```json
{
  "detail": "错误描述信息"
}
```

## 注意事项

1. **任务超时**：用户输入等待超时时间为 300 秒（5 分钟）
2. **状态存储**：运行中任务状态存储在内存，完成后自动保存到文件系统
3. **服务重启**：重启后可以从文件系统加载已完成的任务状态
4. **并发**：支持多任务并发执行，每个任务有独立的 task_id
5. **WebSocket 重连**：建议前端实现 WebSocket 断线重连机制
6. **定期监控**：服务每5秒检查一次任务进程状态，自动清理已完成的任务
