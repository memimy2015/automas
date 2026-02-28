## 工具 Mock 使用说明

### 1. 开关控制
通过环境变量 `IS_MOCK_ENABLED` 控制是否启用 mock：
- `IS_MOCK_ENABLED=1` 启用 mock
- 其他值（或不设置）默认关闭

### 2. Mock 配置文件位置
mock 文件固定读取：
```
automas/mock/tool_mock.json
```

如果该文件不存在，mock 会保持开启但不会命中任何规则。

### 3. Mock 配置格式
mock 文件是一个 JSON 对象，键是“工具名 + 参数序列化”的组合，值是 mock 返回结果。

键格式：
```
{tool_name}:{json.dumps(args, ensure_ascii=False, sort_keys=True)}
```

示例：
```json
{
  "command:{\"command\":\"ls\"}": "file1.txt\nfile2.txt",
  "read_file:{\"file_path\":\"/tmp/a.txt\"}": "hello",  
  "write_file:{\"file_path\":\"/tmp/b.txt\",\"content\":\"hi\"}": "ok",
  "update_progress:{\"info\":\"step-1\"}": "ok",
  "call_user:{\"query\":\"请选择A或B\",\"invoker_agent_id\":1,\"in_channel\":\"PlannerAgent_1_main\",\"out_channel\":\"user\"}": "A"
}
```

### 4. 未命中行为
当 `IS_MOCK_ENABLED=1` 且未命中任何 key 时，会直接返回：
```
MOCK_NOT_FOUND: {tool_name}
```

用于提示当前缺少对应 mock 规则。

### 5. 常见用法
1) 录制一次真实执行的工具参数  
2) 将参数填入 `tool_mock.json`  
3) 开启 `IS_MOCK_ENABLED=1` 重复运行，得到稳定结果

