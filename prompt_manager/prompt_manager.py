import hashlib
import json
import os
import re
import shutil
import threading
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path, PureWindowsPath
from typing import Any, Dict, Optional, Tuple
from uuid import uuid4
from typing import Optional
from config.logger import setup_logger


_NAME_SAFE_RE = re.compile(r"[^a-zA-Z0-9._-]+")
_WIN_ABS_RE = re.compile(r"^[a-zA-Z]:[\\/]")
_WIN_UNC_RE = re.compile(r"^\\\\")

logger = setup_logger("PromptManager")


def _utc_now_iso() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def _safe_name(name: str) -> str:
    name = name.strip()
    if not name:
        raise ValueError("prompt name is empty")
    return _NAME_SAFE_RE.sub("_", name)


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _looks_like_windows_abs_path(s: str) -> bool:
    return bool(_WIN_ABS_RE.match(s) or _WIN_UNC_RE.match(s))


def _windows_path_to_wsl_mount(s: str) -> Optional[Path]:
    if not _looks_like_windows_abs_path(s):
        return None
    if _WIN_UNC_RE.match(s):
        return None
    wp = PureWindowsPath(s)
    drive = (wp.drive or "").rstrip(":").lower()
    if not drive:
        return None
    parts = [p for p in wp.parts if p not in (wp.drive, "\\", "/")]
    return Path("/mnt") / drive / Path(*parts)


def _project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _default_store_root() -> Path:
    return Path(__file__).resolve().parent / "prompt_store"


def _legacy_store_root() -> Path:
    return _project_root() / "tmp_evaluate" / "prompt_store"


@dataclass(frozen=True)
class PromptVersion:
    name: str
    version: str
    uri: str
    created_at: str
    note: Optional[str]
    sha256: str


class PromptManager:
    def __init__(self, root_dir: str | os.PathLike):
        self.root_dir = Path(root_dir)
        self.prompts_dir = self.root_dir / "prompts"
        self.registry_path = self.root_dir / "registry.json"
        self._lock = threading.RLock()
        self._warned_default_fallback: set[str] = set()
        self.prompts_dir.mkdir(parents=True, exist_ok=True)
        if not self.registry_path.exists():
            self._write_registry({"schema_version": 1, "prompts": {}})
        else:
            _ = self._read_registry()
            self._normalize_registry_paths()

    def _read_registry(self) -> Dict[str, Any]:
        with self._lock:
            data = json.loads(self.registry_path.read_text(encoding="utf-8"))
            if data.get("schema_version") != 1:
                raise ValueError(f"unsupported registry schema_version: {data.get('schema_version')}")
            if "prompts" not in data or not isinstance(data["prompts"], dict):
                raise ValueError("invalid registry: prompts missing")
            return data

    def _write_registry(self, data: Dict[str, Any]) -> None:
        with self._lock:
            tmp_path = self.registry_path.with_suffix(".json.tmp")
            tmp_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            tmp_path.replace(self.registry_path)

    def _normalize_registry_paths(self) -> None:
        with self._lock:
            registry = self._read_registry()
            changed = False
            for _, entry in registry.get("prompts", {}).items():
                versions = entry.get("versions", {})
                if not isinstance(versions, dict):
                    continue
                for _, meta in versions.items():
                    if not isinstance(meta, dict):
                        continue
                    uri = meta.get("uri")
                    if not isinstance(uri, str) or not uri:
                        continue
                    p = Path(uri)
                    if not p.is_absolute():
                        wsl_p = _windows_path_to_wsl_mount(uri)
                        if wsl_p is None:
                            continue
                        p = wsl_p
                    try:
                        rel = p.relative_to(self.root_dir)
                    except Exception:
                        continue
                    meta["uri"] = rel.as_posix()
                    changed = True
            if changed:
                self._write_registry(registry)

    def _ensure_prompt_entry(self, registry: Dict[str, Any], name: str) -> Dict[str, Any]:
        prompts = registry["prompts"]
        if name not in prompts:
            prompts[name] = {
                "safe_name": _safe_name(name),
                "active_version": None,
                "versions": {},
            }
        return prompts[name]

    def list_prompts(self) -> Dict[str, Dict[str, Any]]:
        registry = self._read_registry()
        return registry["prompts"]

    def list_versions(self, prompt_name: str) -> Dict[str, PromptVersion]:
        registry = self._read_registry()
        entry = registry["prompts"].get(prompt_name)
        if not entry:
            return {}
        out: Dict[str, PromptVersion] = {}
        for version, meta in entry.get("versions", {}).items():
            out[version] = PromptVersion(
                name=prompt_name,
                version=version,
                uri=meta["uri"],
                created_at=meta["created_at"],
                note=meta.get("note"),
                sha256=meta["sha256"],
            )
        return out

    def get_active_version(self, prompt_name: str) -> Optional[str]:
        registry = self._read_registry()
        entry = registry["prompts"].get(prompt_name)
        if not entry:
            return None
        return entry.get("active_version")

    def set_active_version(self, prompt_name: str, version: str) -> None:
        with self._lock:
            registry = self._read_registry()
            entry = self._ensure_prompt_entry(registry, prompt_name)
            if version not in entry["versions"]:
                raise KeyError(f"prompt version not found: {prompt_name}@{version}")
            entry["active_version"] = version
            self._write_registry(registry)

    def save_version(self, prompt_name: str, content: str, note: str | None = None, activate: bool = True) -> PromptVersion:
        content = content if content is not None else ""
        sha256 = _sha256_text(content)
        version = datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f") + "_" + uuid4().hex[:8]
        created_at = _utc_now_iso()

        with self._lock:
            registry = self._read_registry()
            entry = self._ensure_prompt_entry(registry, prompt_name)
            safe = entry["safe_name"]
            prompt_dir = self.prompts_dir / safe
            prompt_dir.mkdir(parents=True, exist_ok=True)
            prompt_path = prompt_dir / f"{version}.txt"
            prompt_path.write_text(content, encoding="utf-8")
            uri = prompt_path.relative_to(self.root_dir).as_posix()
            entry["versions"][version] = {
                "uri": uri,
                "created_at": created_at,
                "note": note,
                "sha256": sha256,
            }
            if activate:
                entry["active_version"] = version
            self._write_registry(registry)

        return PromptVersion(
            name=prompt_name,
            version=version,
            uri=uri,
            created_at=created_at,
            note=note,
            sha256=sha256,
        )

    def _resolve(self, prompt_name: str, version: Optional[str]) -> Tuple[Optional[str], Optional[Path]]:
        registry = self._read_registry()
        entry = registry["prompts"].get(prompt_name)
        if not entry:
            return None, None
        selected = version or entry.get("active_version")
        if not selected:
            return None, None
        meta = entry["versions"].get(selected)
        if not meta:
            return None, None
        uri = meta.get("uri")
        if not isinstance(uri, str) or not uri:
            return None, None
        p = Path(uri)
        if p.is_absolute():
            return selected, p
        wsl_p = _windows_path_to_wsl_mount(uri)
        if wsl_p is not None:
            return selected, wsl_p
        return selected, self.root_dir / p

    def get(self, prompt_name: str, default: Optional[str] = None, version: Optional[str] = None) -> str:
        _, path = self._resolve(prompt_name, version)
        if not path:
            if default is None:
                raise KeyError(f"prompt not found and no default provided: {prompt_name}")
            if prompt_name not in self._warned_default_fallback:
                self._warned_default_fallback.add(prompt_name)
                logger.warning(
                    "Prompt fallback to default: name=%s version=%s store=%s",
                    prompt_name,
                    version or "active",
                    str(self.root_dir),
                )
            return default
        return path.read_text(encoding="utf-8")

    def render(self, prompt_name: str, default: Optional[str] = None, version: Optional[str] = None, *args: Any, **kwargs: Any) -> str:
        template = self.get(prompt_name=prompt_name, default=default, version=version)
        return template.format(*args, **kwargs)

    def rollback(self, prompt_name: str, steps: int = 1) -> Optional[str]:
        if steps <= 0:
            raise ValueError("steps must be >= 1")
        with self._lock:
            registry = self._read_registry()
            entry = registry["prompts"].get(prompt_name)
            if not entry:
                return None
            active = entry.get("active_version")
            versions: Dict[str, Dict[str, Any]] = entry.get("versions", {})
            if not versions or not active:
                return None
            ordered = sorted(versions.items(), key=lambda kv: kv[1].get("created_at", ""))
            ids = [vid for vid, _ in ordered]
            if active not in ids:
                return None
            idx = ids.index(active)
            new_idx = idx - steps
            if new_idx < 0:
                new_idx = 0
            entry["active_version"] = ids[new_idx]
            self._write_registry(registry)
            return entry["active_version"]


_DEFAULT_PM: PromptManager | None = None


def _maybe_migrate_legacy_store(dst_root: Path) -> None:
    legacy = _legacy_store_root()
    if not legacy.exists():
        return
    if dst_root.exists():
        if (dst_root / "registry.json").exists():
            return
    dst_root.mkdir(parents=True, exist_ok=True)
    shutil.copytree(legacy, dst_root, dirs_exist_ok=True)


def get_prompt_manager() -> PromptManager:
    global _DEFAULT_PM
    if _DEFAULT_PM is None:
        env_root = os.getenv("AUTOMAS_PROMPT_STORE_DIR", "").strip()
        root = Path(env_root).expanduser() if env_root else _default_store_root()
        root = root.resolve()
        _maybe_migrate_legacy_store(root)
        _DEFAULT_PM = PromptManager(root_dir=root)
    return _DEFAULT_PM
