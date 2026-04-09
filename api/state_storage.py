"""
StateStorage - 状态存储（内存 + 文件持久化）
"""

import os
import json
from typing import Dict, Any, Optional
from datetime import datetime


class StateStorage:
    """
    状态存储 - 支持内存缓存和文件持久化
    """
    _states: Dict[str, dict] = {}  # task_id -> state (内存缓存)
    _completed_tasks: set = set()  # 已完成的任务ID集合
    
    # 存储路径配置
    BASE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "storage", "tasks")
    COMPLETED_DIR = os.path.join(BASE_DIR, "completed")
    INDEX_FILE = os.path.join(COMPLETED_DIR, "index.json")

    @classmethod
    def _ensure_dirs(cls):
        """确保存储目录存在"""
        os.makedirs(cls.COMPLETED_DIR, exist_ok=True)

    @classmethod
    def _get_state_file_path(cls, task_id: str) -> str:
        """获取任务状态文件路径"""
        return os.path.join(cls.COMPLETED_DIR, f"{task_id}.json")

    @classmethod
    def _save_index(cls):
        """保存已完成任务索引"""
        cls._ensure_dirs()
        index_data = {
            "task_ids": list(cls._completed_tasks),
            "updated_at": datetime.now().isoformat()
        }
        with open(cls.INDEX_FILE, "w", encoding="utf-8") as f:
            json.dump(index_data, f, ensure_ascii=False, indent=2)

    @classmethod
    def _load_index(cls) -> set:
        """加载已完成任务索引"""
        if not os.path.exists(cls.INDEX_FILE):
            return set()
        try:
            with open(cls.INDEX_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return set(data.get("task_ids", []))
        except Exception:
            return set()

    @classmethod
    def _save_state_to_file(cls, task_id: str, state: dict):
        """将状态保存到文件"""
        cls._ensure_dirs()
        file_path = cls._get_state_file_path(task_id)
        
        # 调试信息
        print(f"[StateStorage] _save_state_to_file: task_id={task_id}")
        print(f"[StateStorage] State keys before save: {list(state.keys()) if isinstance(state, dict) else 'Not a dict'}")
        
        # 添加元数据
        state_with_meta = {
            "task_id": task_id,
            "saved_at": datetime.now().isoformat(),
            "state": state
        }
        
        print(f"[StateStorage] Saving to file: {file_path}")
        
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(state_with_meta, f, ensure_ascii=False, indent=2)
        
        print(f"[StateStorage] File saved successfully")

    @classmethod
    def _load_state_from_file(cls, task_id: str) -> Optional[dict]:
        """从文件加载状态"""
        file_path = cls._get_state_file_path(task_id)
        if not os.path.exists(file_path):
            return None
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("state")
        except Exception:
            return None

    @classmethod
    def save(cls, task_id: str, state: dict):
        """
        保存状态到内存（创建深拷贝，确保状态变化可被检测）

        Args:
            task_id: 任务ID
            state: 状态数据
        """
        import copy
        cls._states[task_id] = copy.deepcopy(state)

    @classmethod
    def get(cls, task_id: str) -> Optional[dict]:
        """
        获取状态 - 先查内存，再查文件

        Args:
            task_id: 任务ID

        Returns:
            状态数据，不存在返回 None
        """
        # 先查内存
        if task_id in cls._states:
            return cls._states[task_id]
        
        # 再查文件（可能是已完成的任务）
        state = cls._load_state_from_file(task_id)
        if state:
            # 缓存到内存
            cls._states[task_id] = state
        return state

    @classmethod
    def delete(cls, task_id: str):
        """
        删除状态（内存和文件）

        Args:
            task_id: 任务ID
        """
        cls._states.pop(task_id, None)
        cls._completed_tasks.discard(task_id)
        cls._save_index()
        # 删除文件
        file_path = cls._get_state_file_path(task_id)
        if os.path.exists(file_path):
            os.remove(file_path)

    @classmethod
    def get_all_task_ids(cls) -> list:
        """
        获取所有任务ID（包括内存中的和已完成的）

        Returns:
            任务ID列表
        """
        # 加载已完成任务索引
        completed = cls._load_index()
        cls._completed_tasks = completed
        
        # 合并内存中的和已完成的任务ID
        all_ids = set(cls._states.keys()) | completed
        return list(all_ids)

    @classmethod
    def mark_task_completed(cls, task_id: str, final_state: dict = None):
        """
        标记任务为已完成，保存到文件系统

        Args:
            task_id: 任务ID
            final_state: 最终状态（如果为None则使用内存中的状态）
        """
        state = final_state or cls._states.get(task_id)
        if not state:
            print(f"[StateStorage] mark_task_completed: No state found for task {task_id}")
            return

        # 调试信息
        print(f"[StateStorage] mark_task_completed for task {task_id}")
        print(f"[StateStorage] Input state keys: {list(state.keys()) if isinstance(state, dict) else 'Not a dict'}")
        print(f"[StateStorage] Memory state exists: {task_id in cls._states}")
        if task_id in cls._states:
            print(f"[StateStorage] Memory state keys: {list(cls._states[task_id].keys())}")

        # 确保状态包含完整的字段
        # 如果传入的 state 不完整，尝试从内存中获取完整状态
        if task_id in cls._states:
            full_state = cls._states[task_id]
            # 合并状态，确保保留完整信息
            if isinstance(state, dict) and isinstance(full_state, dict):
                # 使用完整状态保存
                state_to_save = full_state
                print(f"[StateStorage] Using full state from memory")
            else:
                state_to_save = state
                print(f"[StateStorage] Using input state (not dict)")
        else:
            state_to_save = state
            print(f"[StateStorage] Using input state (not in memory)")

        print(f"[StateStorage] Final state_to_save keys: {list(state_to_save.keys()) if isinstance(state_to_save, dict) else 'Not a dict'}")

        # 保存到文件
        cls._save_state_to_file(task_id, state_to_save)

        # 添加到已完成集合
        cls._completed_tasks.add(task_id)
        cls._save_index()

        # 从内存中移除（可选，保留也可以）
        # cls._states.pop(task_id, None)

    @classmethod
    def is_task_really_completed(cls, task_id: str) -> bool:
        """
        检查任务是否真正完成（summary_body 有值）

        Args:
            task_id: 任务ID

        Returns:
            是否真正完成（summarizer 已生成总结）
        """
        state = cls.get(task_id)
        if not state:
            return False

        # 检查 summary_body 是否存在且非空
        summary_body = state.get("summary_body", "")
        if isinstance(summary_body, str):
            return len(summary_body.strip()) > 0
        elif isinstance(summary_body, dict):
            # 如果是 dict，检查 content 字段
            content = summary_body.get("content", "")
            return len(str(content).strip()) > 0

        return False

    @classmethod
    def is_task_completed(cls, task_id: str) -> bool:
        """
        检查任务是否已完成

        Args:
            task_id: 任务ID

        Returns:
            是否已完成
        """
        if task_id in cls._completed_tasks:
            return True
        # 检查索引文件
        completed = cls._load_index()
        return task_id in completed

    @classmethod
    def get_completed_task_ids(cls) -> list:
        """
        获取所有已完成的任务ID

        Returns:
            已完成任务ID列表
        """
        cls._completed_tasks = cls._load_index()
        return list(cls._completed_tasks)
