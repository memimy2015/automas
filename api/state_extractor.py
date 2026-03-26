"""
StateExtractor - 从 ContextManager 提取状态，组装为前端需要的 JSON 格式
"""

from typing import Dict, List, Any, Optional


class StateExtractor:
    """
    从 ContextManager 提取状态，组装为前端需要的 JSON 格式
    """

    @staticmethod
    def extract(context_manager, task_id: str) -> dict:
        """
        提取完整状态

        Args:
            context_manager: ContextManager 实例
            task_id: 任务ID

        Returns:
            符合前端要求的 JSON 格式
        """
        return {
            "task_id": task_id,
            "chat_body": StateExtractor._extract_chat_body(context_manager),
            "plan_body": StateExtractor._extract_plan_body(context_manager),
            "current_subagent": StateExtractor._extract_current_subagent(context_manager),
            "summary_body": StateExtractor._extract_summary(context_manager)
        }

    @staticmethod
    def _extract_chat_body(context_manager) -> List[Dict[str, str]]:
        """
        从 dialogue_history["user"] 提取对话历史

        根据 content 前缀判断 role 名称：
        - "澄清者: " -> 澄清者
        - "规划者: " -> 规划者
        - "总结者: " -> 总结者
        - "{role_name}: " -> role_name（执行 Agent）
        """
        dialogue_history = context_manager.dialogue_history
        user_channel = dialogue_history.get("user", [])

        chat_body = []

        for msg in user_channel:
            role = msg.get("role")
            content = msg.get("content", "")

            if role == "user":
                chat_body.append({
                    "role": "user",
                    "content": content
                })
            elif role == "assistant":
                agent_role, clean_content = StateExtractor._parse_agent_message(content)
                chat_body.append({
                    "role": agent_role,
                    "content": clean_content
                })

        return chat_body

    @staticmethod
    def _parse_agent_message(content: str) -> tuple:
        """
        解析 Agent 消息，返回 (role_name, clean_content)

        前缀规则（根据 notifier.py）：
        - "澄清者: " -> 澄清者
        - "规划者: " -> 规划者
        - "总结者: " -> 总结者
        - "{role_name}: " -> role_name（执行 Agent，role_name 来自 factory_output）
        """
        # 固定角色的前缀
        fixed_prefixes = {
            "澄清者: ": "澄清者",
            "规划者: ": "规划者",
            "总结者: ": "总结者",
        }

        for prefix, role_name in fixed_prefixes.items():
            if content.startswith(prefix):
                return role_name, content[len(prefix):].strip()

        # 执行 Agent: "{role_name}: "
        if ": " in content:
            colon_idx = content.index(": ")
            role_name = content[:colon_idx]
            clean_content = content[colon_idx + 2:].strip()
            return role_name, clean_content

        # 未知类型，原样返回
        return "assistant", content

    @staticmethod
    def _extract_plan_body(context_manager) -> dict:
        """
        从 task_state 提取计划状态
        """
        task_state = context_manager.task_state

        return {
            "tasks": StateExtractor._extract_tasks(task_state.tasks),
            "next_step": {
                "objective_index": task_state.next_step.objective_index,
                "sub_objective_index": task_state.next_step.sub_objective_index
            },
            "is_mission_accomplished": task_state.is_mission_accomplished,
            "overall_goal": task_state.overall_goal
        }

    @staticmethod
    def _extract_tasks(tasks: list) -> List[dict]:
        """
        提取任务列表
        """
        result = []
        for task in tasks:
            task_obj = {
                "task_name": task.task_name,
                "finished": task.finished,
                "objective": []
            }

            for step in task.objective:
                step_obj = {
                    "sub_objective": step.sub_objective,
                    "status": step.status,
                    "milestones": step.milestones,
                    "resource_reference": [
                        {
                            "description": r.description,
                            "URI": r.URI,
                            "type": r.type
                        }
                        for r in step.resource_reference
                    ],
                    "execution_summary": step.execution_summary,
                    "agent_id": step.agent_id
                }
                task_obj["objective"].append(step_obj)

            result.append(task_obj)

        return result

    @staticmethod
    def _extract_current_subagent(context_manager) -> Optional[dict]:
        """
        提取当前正在执行的 subagent 信息
        """
        factory_output = context_manager.latest_agent_factory_output
        if not factory_output:
            return None

        # 获取当前 step 的 milestones
        task_state = context_manager.task_state
        obj_idx = task_state.next_step.objective_index
        sub_idx = task_state.next_step.sub_objective_index

        exec_info = []
        if obj_idx < len(task_state.tasks):
            task = task_state.tasks[obj_idx]
            if sub_idx < len(task.objective):
                exec_info = task.objective[sub_idx].milestones

        return {
            "role_name": factory_output.role_name,
            "role_setting": factory_output.role_setting,
            "task_specification": factory_output.task_specification,
            "exec_info": exec_info
        }

    @staticmethod
    def _extract_summary(context_manager) -> str:
        """
        提取最终总结
        从 Summarizer channel 获取
        """
        try:
            summarizer_channel = context_manager.consistentAgent2DefaultChannel["Summarizer"]
            for channel, messages in context_manager.dialogue_history.items():
                if channel == summarizer_channel:
                    for msg in reversed(messages):
                        if msg.get("role") == "assistant":
                            content = msg.get("content", "")
                            # 如果是 dict，提取 content 字段
                            if isinstance(content, dict):
                                return content.get("content", "")
                            return content
        except Exception as e:
            print(f"Error extracting summary: {e}")
        return ""
