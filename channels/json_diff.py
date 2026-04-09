import json
from typing import Any, List, Tuple


def _is_primitive(v: Any) -> bool:
    return v is None or isinstance(v, (bool, int, float, str))


def _fmt_value(v: Any, max_len: int = 200) -> str:
    if _is_primitive(v):
        s = json.dumps(v, ensure_ascii=False)
    else:
        try:
            s = json.dumps(v, ensure_ascii=False)
        except Exception:
            s = repr(v)
    if len(s) > max_len:
        return s[: max_len - 3] + "..."
    return s


def diff_json(old: Any, new: Any, *, max_changes: int = 30) -> List[Tuple[str, str, str]]:
    changes: List[Tuple[str, str, str]] = []

    def walk(path: str, a: Any, b: Any) -> None:
        if len(changes) >= max_changes:
            return
        if a is b:
            return
        if type(a) != type(b):
            changes.append((path or "$", _fmt_value(a), _fmt_value(b)))
            return
        if _is_primitive(a):
            if a != b:
                changes.append((path or "$", _fmt_value(a), _fmt_value(b)))
            return
        if isinstance(a, dict):
            a_keys = set(a.keys())
            b_keys = set(b.keys())
            for k in sorted(a_keys - b_keys):
                if len(changes) >= max_changes:
                    return
                changes.append((f"{path}.{k}" if path else str(k), _fmt_value(a.get(k)), _fmt_value(None)))
            for k in sorted(b_keys - a_keys):
                if len(changes) >= max_changes:
                    return
                changes.append((f"{path}.{k}" if path else str(k), _fmt_value(None), _fmt_value(b.get(k))))
            for k in sorted(a_keys & b_keys):
                walk(f"{path}.{k}" if path else str(k), a.get(k), b.get(k))
            return
        if isinstance(a, list):
            if len(a) != len(b):
                changes.append((path or "$", f"len={len(a)}", f"len={len(b)}"))
                if len(changes) >= max_changes:
                    return
            for i in range(min(len(a), len(b))):
                walk(f"{path}[{i}]" if path else f"[{i}]", a[i], b[i])
            return
        changes.append((path or "$", _fmt_value(a), _fmt_value(b)))

    walk("", old, new)
    return changes

