import sys
import os
from pathlib import Path
import ast

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from prompt_manager import get_prompt_manager


def _maybe_save(name: str, content: str, force: bool) -> None:
    pm = get_prompt_manager()
    active = pm.get_active_version(name)
    if active is None:
        pm.save_version(prompt_name=name, content=content, note="bootstrap", activate=True)
        return
    if force:
        pm.save_version(prompt_name=name, content=content, note="bootstrap_force", activate=True)


def main() -> None:
    force = os.getenv("PROMPT_BOOTSTRAP_FORCE", "0") == "1"

    def extract_constant(file_path: Path, var_name: str) -> str:
        tree = ast.parse(file_path.read_text(encoding="utf-8"), filename=str(file_path))
        for node in tree.body:
            if not isinstance(node, ast.Assign):
                continue
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == var_name:
                    if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                        return node.value.value
        raise KeyError(f"string constant not found: {file_path}::{var_name}")

    targets = [
        ("planner.system_latest_instruction", ROOT / "control" / "PlannerAgent.py", "LATEST_INSTRUCTION"),
        ("planner.schedule_init", ROOT / "control" / "PlannerAgent.py", "INIT_SCHEDULE"),
        ("planner.schedule_continue", ROOT / "control" / "PlannerAgent.py", "CONTINUE_SCHEDULE"),
        ("planner.schedule_replan", ROOT / "control" / "PlannerAgent.py", "REPLAN_SCHEDULE"),
        ("planner.schedule_pending", ROOT / "control" / "PlannerAgent.py", "PENDING_SCHEDULE"),
        ("Clarifier.system", ROOT / "control" / "ClarifierAgent.py", "DEFAULT_INSTRUCTION"),
        ("summarizer.system", ROOT / "control" / "SummarizerAgent.py", "DEFAULT_INSTRUCTION"),
        ("agent_factory.system", ROOT / "execution" / "factory" / "agent_factory.py", "DEFAULT_INSTRUCTION"),
        ("execution_agent.system_template", ROOT / "execution" / "agent" / "prompt.py", "SYS_PROMPT_TEMPLATE"),
        ("execution_agent.submit_prompt", ROOT / "execution" / "agent" / "agent.py", "DEFAULT_SUBMIT_PROMPT"),
    ]

    for prompt_name, file_path, var_name in targets:
        content = extract_constant(file_path, var_name)
        _maybe_save(prompt_name, content, force)


if __name__ == "__main__":
    main()

