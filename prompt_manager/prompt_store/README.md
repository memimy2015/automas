# Prompt Store（提示词管理器）

本目录用于把项目中的 Prompt 从“写死在代码里”迁移为“文件化 + 可版本化 + 可回滚”的形式，方便你做 agent 优化时频繁调整提示词并快速回退。

## 目录结构

- `registry.json`：注册表（每个 prompt 的版本列表、当前激活版本、元信息）
- `prompts/<prompt_name>/<version>.txt`：每个版本的 prompt 文本

## Prompt 名称约定（当前已接入）

这些名称是代码里读取 prompt 的 key：

- `execution_agent.system_template`：Execution 子代理 system prompt 总模板
- `execution_agent.submit_prompt`：Execution 子代理执行后提交结果的 prompt
- `agent_factory.system`：AgentFactory 的 Prompt Engineer system prompt
- `claimer.system`：Claimer system prompt
- `summarizer.system`：Summarizer system prompt
- `planner.system_latest_instruction`：Planner 的 system prompt（LATEST_INSTRUCTION）
- `planner.schedule_init`：Planner INIT 状态的 schedule prompt
- `planner.schedule_continue`：Planner CONTINUE 状态的 schedule prompt
- `planner.schedule_replan`：Planner REPLAN 状态的 schedule prompt
- `planner.schedule_pending`：Planner PENDING 状态的 schedule prompt

## 关键代码入口

- PromptManager 实现： [prompt_manager.py](file:///c:/Users/Admin/Desktop/20260203/AIME/automas/prompt_manager/prompt_manager.py)
- 初始化落盘脚本： [bootstrap_prompts.py](file:///c:/Users/Admin/Desktop/20260203/AIME/automas/prompt_manager/bootstrap_prompts.py)
- CLI 管理脚本： [prompt_cli.py](file:///c:/Users/Admin/Desktop/20260203/AIME/automas/prompt_manager/prompt_cli.py)
- 更新模板脚本： [prompt_update_template.py](file:///c:/Users/Admin/Desktop/20260203/AIME/automas/prompt_manager/prompt_update_template.py)

## 快速开始

### 1）首次初始化（把代码内置 prompt 落盘到 prompt_store）

在项目根目录 `automas/` 下执行：

```bash
python prompt_manager\bootstrap_prompts.py
```

说明：
- 默认只会在 registry 里“缺失该 prompt”时才写入（避免覆盖你已调整过的版本）
- 如需强制用当前代码常量覆盖并生成新版本：

```bash
set PROMPT_BOOTSTRAP_FORCE=1
python prompt_manager\bootstrap_prompts.py
```

### 2）更新某个 prompt（新增版本并激活）

建议用 Python 小脚本/REPL 操作（不要求改动任何 agent 代码）：

```python
from prompt_manager import get_prompt_manager

pm = get_prompt_manager()

new_text = "..."  # 你的新 prompt 内容
pm.save_version(prompt_name="planner.system_latest_instruction", content=new_text, note="tune planner v1", activate=True)
```

### 3）回滚（切换激活版本到之前的版本）

```python
from prompt_manager import get_prompt_manager

pm = get_prompt_manager()
pm.rollback(prompt_name="planner.system_latest_instruction", steps=1)
```

## CLI 用法

在项目根目录 `automas/` 下执行：

```bash
python prompt_manager\prompt_cli.py list
python prompt_manager\prompt_cli.py versions planner.system_latest_instruction
python prompt_manager\prompt_cli.py active planner.system_latest_instruction
python prompt_manager\prompt_cli.py set planner.system_latest_instruction <version_id>
python prompt_manager\prompt_cli.py rollback planner.system_latest_instruction --steps 1
python prompt_manager\prompt_cli.py get planner.system_latest_instruction
python prompt_manager\prompt_cli.py save planner.system_latest_instruction --file path\to\new_prompt.txt --note "my note"
```

说明：
- `save` 默认会自动激活新版本；如需保存但不切换，加 `--no-activate`
- `save` 不指定 `--file` 时，会从 stdin 读取（可用管道/重定向）

## 启动时指定版本（app.py）

项目启动入口 [app.py](file:///c:/Users/Admin/Desktop/20260203/AIME/automas/app.py) 顶部提供了 `PROMPT_VERSION_OVERRIDES`：

- 把某个 key 的值从 `None` 改成目标 `<version_id>`，启动时会自动切换为该版本
- `None` 表示不覆盖，继续使用当前 store 里激活的版本

## 行为规则（很重要）

- **兼容性**：如果某个 prompt 在 store 里不存在，代码会自动回退到原先写死的常量字符串（确保系统可跑）。
- **渲染方式**：
  - `PromptManager.get(...)`：直接返回文本
  - `PromptManager.render(...)`：返回 `template.format(...)` 的渲染结果
  - 注意：Execution Agent system 模板已改为 **命名占位符**（例如 `{role_setting}`、`{output_dir}`）。为兼容历史版本，代码仍支持旧的 **位置占位符** 模板（多个 `{}`，按固定顺序 `.format(...)`）。

## 自检

```bash
python prompt_manager\prompt_cli.py list
```
