try:
    import msvcrt
except Exception:
    msvcrt = None

try:
    from prompt_toolkit import prompt as pt_prompt
    from prompt_toolkit.patch_stdout import patch_stdout
    _HAS_PROMPT_TOOLKIT = True
except Exception:
    _HAS_PROMPT_TOOLKIT = False


def get_input(prompt: str) -> str:
    if _HAS_PROMPT_TOOLKIT:
        with patch_stdout():
            return pt_prompt(prompt)
    if msvcrt is None:
        return input(prompt)
    print(prompt, end="", flush=True)
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
