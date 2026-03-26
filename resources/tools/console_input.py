import os

try:
    import msvcrt
except Exception:
    msvcrt = None

import shutil
import textwrap

try:
    from prompt_toolkit import prompt as pt_prompt
    from prompt_toolkit.patch_stdout import patch_stdout
    _HAS_PROMPT_TOOLKIT = True
except Exception:
    _HAS_PROMPT_TOOLKIT = False


def get_input(prompt: str) -> str:
    """
    获取用户输入 - 支持命令行模式和网页模式
    """
    # 检查是否在网页模式
    if os.environ.get("AUTOMAS_WEB_MODE") == "1":
        task_id = os.environ.get("AUTOMAS_TASK_ID")
        if not task_id:
            raise RuntimeError("AUTOMAS_TASK_ID not set in web mode")

        # 从缓冲区等待用户响应（阻塞）
        # 注意：prompt 中包含了 Agent 的问题，但 InputBuffer 已经通过 Notifier 注册了
        # 使用 api.input_buffer 中的全局函数（在子进程中通过 set_queue 设置了队列）
        from api.input_buffer import wait_for_response
        return wait_for_response(task_id, timeout=300)

    # 命令行模式（原有逻辑）
    if _HAS_PROMPT_TOOLKIT:
        with patch_stdout():
            print(prompt, end="", flush=True)
            return pt_prompt()
        pass
    if msvcrt is None:
        return input(prompt)
    width = shutil.get_terminal_size((80, 20)).columns
    lines = []
    for part in prompt.splitlines():
        wrapped = textwrap.wrap(
            part,
            width=max(width, 1),
            replace_whitespace=False,
            drop_whitespace=False,
        )
        lines.extend(wrapped if wrapped else [""])
    if not lines:
        lines = [""]
    if len(lines) > 1:
        for line in lines[:-1]:
            print(line)
        print(lines[-1], end="", flush=True)
    else:
        print(lines[0], end="", flush=True)
    buffer = []
    while True:
        ch = msvcrt.getwch()
        if ch in ("\r", "\n"):
            print()
            return "".join(buffer)
        if ch == "\x08":
            if buffer:
                buffer.pop()
                print("\b \b", end="", flush=True)
            continue
        if ch == "\x03":
            raise KeyboardInterrupt
        buffer.append(ch)
        print(ch, end="", flush=True)
