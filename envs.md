## 环境变量清单

### 1. LLM / API 相关
- ARK_API_KEY  
  - 作用：火山引擎 Ark Runtime 的 API Key  
  - 影响范围：`llm/llm.py` 的 LLM 调用初始化  
  - 备注：未设置会导致 LLM 调用失败
  - 获取方式：[火山引擎 Ark Runtime](https://www.volcengine.com/docs/82379/1361424?lang=zh)

- MODEL  
  - 作用：Ark 推理接入点 ID, model_id 或 endpoint_id
  - 影响范围：`llm/llm.py` 的 LLM 调用  
  - 备注：未设置会导致 LLM 调用失败
  - 获取方式：[火山引擎 Ark Runtime](https://www.volcengine.com/docs/82379/1361424?lang=zh)
  
- SEARCH_API_KEY  
  - 作用：Feedcoop 搜索接口的 API Key  
  - 影响范围：`skills/web_scraping/scripts/internet_wide_search.py`  
  - 备注：未设置会返回错误信息
  - 获取方式：[Feedcoop 搜索接口](https://www.volcengine.com/docs/85508/1650263?lang=zh)

### 2. cozeloop - 上报数据

- COZELOOP_API_TOKEN
  - 作用：cozeloop 上报数据的 API Token  
  - 获取方式：扣子罗盘 -> SDK&API -> 授权 -> 个人访问令牌

- COZELOOP_WORKSPACE_ID
  - 作用：cozeloop 工作空间 ID  
  - 获取方式：扣子罗盘 -> 工作空间 -> 指针悬浮在对应的空间标签上，右侧出现复制图标即可复制ID


### 3. BrowserUse Skill
- BROWSER_USE_API_KEY  
  - 作用：browser-use CLI 远程/代理能力的 API Key  
  - 影响范围：`skills/browser-use/SKILL.md`（由 browser-use CLI 读取）  
  - 备注：未设置会影响 browser-use 相关能力

### 4. 运行与调试
- IS_DEBUG_ENABLED  
  - 作用：控制调试模式与自动 dump  
  - 影响范围：`app.py`（启动路径与 auto_dump 启用）、`control/context_manager.py`（auto_dump 与 ID 生成）、`execution/agent/agent.py`（Agent 日志）  
  - 默认值：`1`

- IS_MOCK_ENABLED  
  - 作用：控制工具层 mock 是否启用  
  - 影响范围：`resources/tools/tool_executer.py`  
  - 默认值：`0`

- AUTOMAS_LLM_MAX_RETRIES
  - 作用：自动重试最大次数  
  - 影响范围：`llm/llm.py` 的 LLM 调用  
  - 默认值：`5`

