## 环境变量清单

### 1. LLM / API 相关
- ARK_API_KEY  
  - 作用：火山引擎 Ark Runtime 的 API Key  
  - 影响范围：`llm/llm.py` 的 LLM 调用初始化  
  - 备注：未设置会导致 LLM 调用失败

- MODEL  
  - 作用：Ark 推理接入点 ID  
  - 影响范围：`llm/llm.py` 的 LLM 调用  
  - 备注：未设置会导致 LLM 调用失败

- SEARCH_API_KEY  
  - 作用：Feedcoop 搜索接口的 API Key  
  - 影响范围：`skills/web_scraping/scripts/internet_wide_search.py`  
  - 备注：未设置会返回错误信息

### 2. BrowserUse Skill
- BROWSER_USE_API_KEY  
  - 作用：browser-use CLI 远程/代理能力的 API Key  
  - 影响范围：`skills/browser-use/SKILL.md`（由 browser-use CLI 读取）  
  - 备注：未设置会影响 browser-use 相关能力

- OPENAI_API_KEY  
  - 作用：browser-use 可用的 LLM API Key 示例  
  - 影响范围：`skills/browser-use/SKILL.md`（由 browser-use CLI 读取）  
  - 备注：为外部 CLI 使用，本项目代码未直接读取

- ANTHROPIC_API_KEY  
  - 作用：browser-use 可用的 LLM API Key 示例  
  - 影响范围：`skills/browser-use/SKILL.md`（由 browser-use CLI 读取）  
  - 备注：为外部 CLI 使用，本项目代码未直接读取

### 3. 运行与调试
- IS_DEBUG_ENABLED  
  - 作用：控制调试模式与自动 dump  
  - 影响范围：`app.py`（启动路径与 auto_dump 启用）、`control/context_manager.py`（auto_dump 与 ID 生成）、`execution/agent/agent.py`（Agent 日志）  
  - 默认值：`1`

- IS_MOCK_ENABLED  
  - 作用：控制工具层 mock 是否启用  
  - 影响范围：`resources/tools/tool_executer.py`  
  - 默认值：`0`

### 4. Shell 行为
- SHELL  
  - 作用：指定持久化 Shell 启动的 shell 程序  
  - 影响范围：`resources/tools/persistent_shell.py`  
  - 默认值：`/bin/bash`（Windows 环境下请根据实际可用 shell 调整）
