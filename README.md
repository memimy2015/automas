# Automas

Automas 是一个智能 AI Agent 框架，旨在通过持久化 Shell 环境与您的操作系统进行交互。它由大语言模型（LLM）驱动，能够理解自然语言指令，执行复杂的终端命令序列，并在操作之间保持上下文状态。

## 🚀 核心特性

*   **持久化 Shell 环境**：与标准命令执行工具不同，Automas 维护一个活跃的 Shell 会话（`PersistentShell`）。这使得有状态的操作（如切换目录 `cd`、设置环境变量 `export`）以及多步工作流能够无缝执行。
*   **LLM 驱动的智能代理**：基于火山引擎 Ark Runtime（兼容 OpenAI API）构建，Agent 能够根据用户查询智能规划并执行任务。
*   **模块化架构**：项目结构清晰，实现了 Agent 核心、LLM 接口、工具执行和配置的解耦，易于扩展。
*   **日志系统**：集成日志记录功能（由 `config/logger.py` 提供），可追踪 Shell 会话和系统活动，便于调试和审计。

## 📂 项目结构

```
automas/
├── agent/              # 处理对话循环的核心 Agent 逻辑
│   └── agent.py
├── llm/                # LLM 接口层（集成火山引擎 Ark）
│   └── llm.py
├── resources/
│   └── tools/          # 工具定义与执行逻辑
│       ├── tool_executer.py    # 工具注册与分发器
│       └── persistent_shell.py # 有状态 Shell 实现
├── config/             # 配置与实用工具
│   └── logger.py       # 日志设置
├── app.py              # 主程序入口
├── setup.py            # 包安装配置
└── logs/               # 运行时日志（自动生成）
```

## 🛠️ 安装指南

1.  **克隆仓库**：
    ```bash
    git clone <repository-url>
    cd automas
    ```

## 💻 使用方法
1. 参考 [envs.md](envs.md) 配置环境变量。
2. 按顺序执行以下命令
```bash
source env/env.sh
pip install -r requirements.txt
sh start.sh
```
3. 当看到以下输出时表示启动成功
```bash
Serving HTTP on :: port 5173 (http://[::]:5173/) ...
[InputBuffer] Register consumer started
INFO:     Started server process [34738]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```
4. 启动飞书插件
则需要配置环境变量 `FEISHU_APP_ID` 和 `FEISHU_APP_SECRET`。
启动命令调整为：
```bash
sh start.sh --feishu
```

### 示例

Agent 可以处理如下指令：
> "检查当前目录下有哪些文件。"

Agent 的执行流程：
1.  接收查询。
2.  决策调用 `command` 工具并执行 `ls -l`。
3.  在持久化 Shell 中执行命令。
4.  分析输出并向您反馈文件列表。

### 日志

日志文件会自动生成在 `logs/` 目录下。每次会话都会创建一个带有时间戳的新日志文件（例如 `automas_2023-10-27.log`），记录所有 Shell 命令和系统事件。

## 📄 许可证

[MIT License](LICENSE)
