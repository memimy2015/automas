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
