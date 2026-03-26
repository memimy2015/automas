# tmp_evaluate

用于在本项目内批量评测 ClaimerAgent。

## 批量跑 ClaimerAgent（用例来自 app.py 的 TEST_CASES）

```bash
python -m tmp_evaluate.batch_claimer --cases TEST_CASE_1,TEST_CASE_2 --task-prefix eval
```

常用参数：

- `--all`：跑全部用例
- `--cases ...`：只跑指定用例（逗号分隔）
- `--exclude ...`：排除指定用例（逗号分隔）
- `--max-user-calls N`：限制 Claimer 触发追问次数（避免无限追问）
- `--task-prefix PREFIX`：每个用例的 AUTOMAS_TASK_DIR 前缀

输出：

- `tmp_evaluate/runs/<run_id>/results.jsonl`：逐用例结果
- `tmp_evaluate/runs/<run_id>/summary.json`：汇总
