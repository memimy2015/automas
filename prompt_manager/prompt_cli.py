import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from prompt_manager import get_prompt_manager


def _read_text_arg(file_path: str | None) -> str:
    if file_path:
        return Path(file_path).read_text(encoding="utf-8")
    return sys.stdin.read()


def cmd_list(_: argparse.Namespace) -> int:
    pm = get_prompt_manager()
    prompts = pm.list_prompts()
    for name in sorted(prompts.keys()):
        active = prompts[name].get("active_version")
        versions = prompts[name].get("versions", {})
        print(f"{name}\tactive={active}\tversions={len(versions)}")
    return 0


def cmd_versions(args: argparse.Namespace) -> int:
    pm = get_prompt_manager()
    versions = pm.list_versions(args.prompt_name)
    active = pm.get_active_version(args.prompt_name)
    for v in sorted(versions.values(), key=lambda x: x.created_at):
        flag = "*" if v.version == active else " "
        note = v.note or ""
        print(f"{flag} {v.version}\t{v.created_at}\t{v.sha256[:12]}\t{note}")
    return 0


def cmd_active(args: argparse.Namespace) -> int:
    pm = get_prompt_manager()
    active = pm.get_active_version(args.prompt_name)
    if active is None:
        print("")
        return 0
    print(active)
    return 0


def cmd_set(args: argparse.Namespace) -> int:
    pm = get_prompt_manager()
    pm.set_active_version(args.prompt_name, args.version)
    print(pm.get_active_version(args.prompt_name) or "")
    return 0


def cmd_rollback(args: argparse.Namespace) -> int:
    pm = get_prompt_manager()
    v = pm.rollback(args.prompt_name, steps=args.steps)
    print(v or "")
    return 0


def cmd_get(args: argparse.Namespace) -> int:
    pm = get_prompt_manager()
    text = pm.get(args.prompt_name)
    sys.stdout.write(text)
    if not text.endswith("\n"):
        sys.stdout.write("\n")
    return 0


def cmd_save(args: argparse.Namespace) -> int:
    pm = get_prompt_manager()
    content = _read_text_arg(args.file)
    v = pm.save_version(
        prompt_name=args.prompt_name,
        content=content,
        note=args.note,
        activate=not args.no_activate,
    )
    print(v.version)
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="prompt_cli", add_help=True)
    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("list")
    sp.set_defaults(func=cmd_list)

    sp = sub.add_parser("versions")
    sp.add_argument("prompt_name")
    sp.set_defaults(func=cmd_versions)

    sp = sub.add_parser("active")
    sp.add_argument("prompt_name")
    sp.set_defaults(func=cmd_active)

    sp = sub.add_parser("set")
    sp.add_argument("prompt_name")
    sp.add_argument("version")
    sp.set_defaults(func=cmd_set)

    sp = sub.add_parser("rollback")
    sp.add_argument("prompt_name")
    sp.add_argument("--steps", type=int, default=1)
    sp.set_defaults(func=cmd_rollback)

    sp = sub.add_parser("get")
    sp.add_argument("prompt_name")
    sp.set_defaults(func=cmd_get)

    sp = sub.add_parser("save")
    sp.add_argument("prompt_name")
    sp.add_argument("--file", type=str, default=None)
    sp.add_argument("--note", type=str, default=None)
    sp.add_argument("--no-activate", action="store_true")
    sp.set_defaults(func=cmd_save)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())

