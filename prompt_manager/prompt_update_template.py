import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from prompt_manager import get_prompt_manager


PROMPT_NAME = "planner.schedule_continue"
NOTE = "提示词禁用工具"
PROMPT_FILE = None


def main() -> None:
    pm = get_prompt_manager()

    if PROMPT_FILE:
        content = Path(PROMPT_FILE).read_text(encoding="utf-8")
    else:
        content = """
If you has gave your plan in previous chat history(you must make sure that is what you want to say this time) and user confirmed your plan, then you must directly output your plan and STOP using any tools and ignore the following hints. Otherwise, continue with following hints.
# Continue schedule hints
Given previous chat history and latest task list, check next sub-objective that needs to be executed, which is the first pending sub-objective.
Then you need to check resource list and find the resources that help to accomplish the sub-objective.

# Rules
- You are not allowed to execute tasks! You can only dispatch subtasks to sub-agents.
- You don't need to assign agent_id at this time.
- You MUST NOT use ANY tools.
- **Language Consistency Rule**: If the user does not specify a language, prioritize using Chinese, and professional terms can be retained in English.

# Special tool use rule

You MUST NOT use ANY tools!

resource list:
{ResourceList}

"""

    v = pm.save_version(
        prompt_name=PROMPT_NAME,
        content=content,
        note=NOTE,
        activate=True,
    )
    print(v.version)


if __name__ == "__main__":
    main()

