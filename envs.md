## 环境变量清单

### 1. LLM / API 相关
- ARK_API_KEY  
  - 作用：火山引擎 Ark Runtime 的 API Key  
  - 影响范围：`llm/llm.py` 的 LLM 调用初始化  
  - 备注：未设置会导致 LLM 调用失败
  - 获取方式：[火山引擎 Ark Runtime](https://www.volcengine.com/docs/82379/1361424?lang=zh)
  
- ARK_BASE_URL  
  - 作用：火山引擎 Ark Runtime 的 Base URL  
  - 影响范围：`llm/llm.py` 的 LLM 调用初始化  
  - 备注：未设置会导致 LLM 调用失败
  - 默认值：`https://ark.cn-beijing.volces.com/api/v3`

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
- AUTOMAS_ENABLE_OBSERVE=0
  - 作用：是否上报数据到云端

- AUTOMAS_TRACE_PROVIDER=cozeloop
  - 作用：指定 trace 数据上报提供方为 cozeloop  
  - 影响范围：`execution/agent/agent.py` 的 trace 上报  
  - 可选值：`cozeloop`、`promptpilot`

- COZELOOP_API_TOKEN
  - 作用：cozeloop 上报数据的 API Token  
  - 获取方式：扣子罗盘 -> SDK&API -> 授权 -> 个人访问令牌

- COZELOOP_WORKSPACE_ID
  - 作用：cozeloop 工作空间 ID  
  - 获取方式：扣子罗盘 -> 工作空间 -> 指针悬浮在对应的空间标签上，右侧出现复制图标即可复制ID

### 3. promptpilot - 上报 trace 数据

- AGENTPILOT_API_URL
  - 作用：PromptPilot 服务地址（用于 traces 上报）
  - 默认值：`https://prompt-pilot.cn-beijing.volces.com`

- AGENTPILOT_API_KEY
  - 作用：PromptPilot API Key（用于鉴权）
  - 获取方式：[PromptPilot](https://promptpilot.volcengine.com/workstation/settings/) -> API Key

- AGENTPILOT_PROJECT_ID
  - 作用：PromptPilot Project ID（用于标识项目）
  - 获取方式：打开 PromptPilot 网站 -> 点击AI Studio -> 左上角项目名展开 -> 复制项目 ID

### 5. 运行与调试
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

- AUTOMAS_API_BASE=http://127.0.0.1:8000
  - 作用：automas服务端接口地址

### 6. 飞书相关
- FEISHU_APP_ID
  - 作用：飞书应用 ID  
  - 影响范围：`channels/feishu.py` 的飞书 API 调用初始化  
- FEISHU_APP_SECRET
  - 作用：飞书应用密钥  
  - 影响范围：`channels/feishu.py` 的飞书 API 调用初始化  
- FEISHU_POLL_INTERVAL_SECONDS=5
  - 作用：飞书轮询间隔（秒）  
  - 影响范围：`channels/feishu.py` 的飞书 API 调用初始化  
- FEISHU_SESSION_PATH
  - 作用：飞书会话存储路径，本地文件路径  
  - 影响范围：`channels/feishu.py` 的飞书会话管理  
  - 示例：/Users/bytedance/automas/storage/feishu_session.json
- PYTHONHTTPSVERIFY=0
  - 作用：禁用 Python HTTPS 验证  
  - 影响范围：`channels/feishu.py` 的飞书 API 调用初始化  
  - 默认值：`0`
