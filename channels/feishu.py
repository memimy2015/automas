import asyncio
import hashlib
import json
import os
import ssl
import threading
from typing import Any, Dict, Optional

import lark_oapi as lark
from lark_oapi import LogLevel
from lark_oapi.event.dispatcher_handler import EventDispatcherHandler
from lark_oapi.api.im.v1 import (
    CreateMessageRequest,
    CreateMessageRequestBody,
    PatchMessageRequest,
    PatchMessageRequestBody,
    ReplyMessageRequest,
    ReplyMessageRequestBody,
)

from .automas_api import AutomasApiClient
from .json_diff import diff_json
from .session_store import BotSession, SessionStore


def _apply_insecure_ssl_patch_if_enabled() -> None:
    if os.environ.get("PYTHONHTTPSVERIFY", "").strip() != "0":
        return

    try:
        import requests

        if not getattr(requests.sessions.Session.request, "_automas_insecure_patched", False):
            orig_request = requests.sessions.Session.request

            def request_wrapper(self, method, url, **kwargs):
                kwargs.setdefault("verify", False)
                return orig_request(self, method, url, **kwargs)

            request_wrapper._automas_insecure_patched = True
            requests.sessions.Session.request = request_wrapper
    except Exception:
        pass

    try:
        import lark_oapi.ws.client as lark_ws_client

        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        if not getattr(lark_ws_client.websockets.connect, "_automas_insecure_patched", False):
            orig_connect = lark_ws_client.websockets.connect

            def connect_wrapper(*args, **kwargs):
                kwargs.setdefault("ssl", ctx)
                return orig_connect(*args, **kwargs)

            connect_wrapper._automas_insecure_patched = True
            lark_ws_client.websockets.connect = connect_wrapper
    except Exception:
        pass


def _strip_chat_body(value: Any) -> Any:
    if isinstance(value, dict):
        out: Dict[str, Any] = {}
        for k, v in value.items():
            if k == "chat_body":
                continue
            out[k] = _strip_chat_body(v)
        return out
    if isinstance(value, list):
        return [_strip_chat_body(v) for v in value]
    return value


def _focus_state_for_push(state_payload: Any) -> Dict[str, Any]:
    if isinstance(state_payload, dict) and isinstance(state_payload.get("state"), dict):
        state_payload = state_payload["state"]
    if not isinstance(state_payload, dict):
        return {"plan_body": None, "current_subagent": None}
    return {
        "plan_body": state_payload.get("plan_body"),
        "current_subagent": state_payload.get("current_subagent"),
    }


def _path_tokens(path: str) -> list[Any]:
    p = (path or "").strip()
    if p == "$":
        return []
    if p.startswith("$."):
        p = p[2:]
    elif p.startswith("$"):
        p = p[1:]
    if not p:
        return []
    tokens: list[Any] = []
    for part in p.split("."):
        if not part:
            continue
        i = 0
        key = ""
        while i < len(part) and part[i] != "[":
            key += part[i]
            i += 1
        if key:
            tokens.append(key)
        while i < len(part):
            if part[i] != "[":
                i += 1
                continue
            j = part.find("]", i + 1)
            if j == -1:
                break
            idx_raw = part[i + 1 : j]
            try:
                tokens.append(int(idx_raw))
            except Exception:
                pass
            i = j + 1
    return tokens


def _get_value_by_path(root: Any, path: str) -> Any:
    cur: Any = root
    for tok in _path_tokens(path):
        if isinstance(tok, int):
            if not isinstance(cur, list) or tok < 0 or tok >= len(cur):
                return None
            cur = cur[tok]
        else:
            if not isinstance(cur, dict) or tok not in cur:
                return None
            cur = cur[tok]
    return cur


def _parse_feishu_text(message_content_json: str) -> str:
    try:
        content = json.loads(message_content_json)
    except Exception:
        return ""
    text = ""
    if isinstance(content, dict) and "text" in content:
        text = content.get("text") or ""
    elif isinstance(content, dict) and "content" in content and isinstance(content.get("content"), list):
        paragraphs: list[str] = []
        for paragraph in content["content"]:
            if not isinstance(paragraph, list):
                continue
            parts: list[str] = []
            for element in paragraph:
                if not isinstance(element, dict):
                    continue
                if element.get("tag") in ("text", "at"):
                    v = element.get("text", "")
                    if v:
                        parts.append(v)
            if parts:
                paragraphs.append(" ".join(parts))
        text = "\n\n".join(paragraphs)
    return str(text).strip()


def _build_card_content(markdown: str) -> str:
    card = {"config": {"wide_screen_mode": True, "update_multi": True}, "elements": [{"tag": "markdown", "content": markdown}]}
    return json.dumps(card, ensure_ascii=False)


class FeishuMessenger:
    def __init__(self, api_client: lark.Client):
        self._api_client = api_client

    async def reply_markdown(self, message_id: str, markdown: str, *, reply_in_thread: bool = True) -> Optional[str]:
        content = _build_card_content(markdown)
        request = (
            ReplyMessageRequest.builder()
            .message_id(message_id)
            .request_body(ReplyMessageRequestBody.builder().msg_type("interactive").content(content).reply_in_thread(reply_in_thread).build())
            .build()
        )
        resp = await asyncio.to_thread(self._api_client.im.v1.message.reply, request)
        data = getattr(resp, "data", None)
        return getattr(data, "message_id", None)

    async def create_markdown(self, chat_id: str, markdown: str) -> Optional[str]:
        content = _build_card_content(markdown)
        request = (
            CreateMessageRequest.builder()
            .receive_id_type("chat_id")
            .request_body(CreateMessageRequestBody.builder().receive_id(chat_id).msg_type("interactive").content(content).build())
            .build()
        )
        resp = await asyncio.to_thread(self._api_client.im.v1.message.create, request)
        data = getattr(resp, "data", None)
        return getattr(data, "message_id", None)

    async def patch_markdown(self, message_id: str, markdown: str) -> None:
        content = _build_card_content(markdown)
        request = PatchMessageRequest.builder().message_id(message_id).request_body(PatchMessageRequestBody.builder().content(content).build()).build()
        await asyncio.to_thread(self._api_client.im.v1.message.patch, request)


class FeishuAutomasBot:
    def __init__(
        self,
        *,
        app_id: str,
        app_secret: str,
        automas_api_base: str,
        session_path: str,
        poll_interval_s: float = 5.0,
    ):
        _apply_insecure_ssl_patch_if_enabled()
        self._app_id = app_id
        self._app_secret = app_secret
        self._poll_interval_s = poll_interval_s
        self._store = SessionStore(session_path)
        self._api = AutomasApiClient(automas_api_base)
        self._lark_api = lark.Client.builder().app_id(app_id).app_secret(app_secret).log_level(LogLevel.INFO).build()
        self._messenger = FeishuMessenger(self._lark_api)

        self._main_loop: Optional[asyncio.AbstractEventLoop] = None
        self._ws_thread: Optional[threading.Thread] = None
        self._ws_client: Optional[lark.ws.Client] = None
        self._stop_event = threading.Event()

        self._guard = asyncio.Lock()
        self._monitor_task: Optional[asyncio.Task] = None
        self._last_state_for_diff: Any = None

    async def start(self) -> None:
        self._main_loop = asyncio.get_running_loop()
        await self._api.wait_server_ready()
        await self._resume_if_needed()
        self._start_ws_thread()

    async def stop(self) -> None:
        self._stop_event.set()
        if self._ws_client:
            try:
                await asyncio.to_thread(self._ws_client.stop)
            except Exception:
                pass
        if self._ws_thread and self._ws_thread.is_alive():
            await asyncio.to_thread(self._ws_thread.join, 2)
        if self._monitor_task and not self._monitor_task.done():
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except Exception:
                pass
        await self._api.aclose()

    def _start_ws_thread(self) -> None:
        dispatcher = (
            EventDispatcherHandler.builder(self._app_id, self._app_secret, LogLevel.INFO)
            .register_p2_im_message_receive_v1(self._on_message)
            .build()
        )
        self._ws_client = lark.ws.Client(self._app_id, self._app_secret, event_handler=dispatcher)

        t = threading.Thread(target=self._run_ws, name="feishu-ws", daemon=True)
        self._ws_thread = t
        t.start()

    def _run_ws(self) -> None:
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                import lark_oapi.ws.client as lark_ws_client

                lark_ws_client.loop = loop
            except Exception:
                pass
            _apply_insecure_ssl_patch_if_enabled()
            if self._ws_client:
                self._ws_client.start()
        except Exception:
            pass

    def _on_message(self, event) -> None:
        try:
            message = event.event.message
            chat_id = message.chat_id
            msg_id = message.message_id
            text = _parse_feishu_text(message.content)
            if not text:
                return
            if self._main_loop and self._main_loop.is_running():
                asyncio.run_coroutine_threadsafe(self._handle_inbound(chat_id, msg_id, text), self._main_loop)
        except Exception:
            return

    async def _resume_if_needed(self) -> None:
        session = self._store.load()
        if not session.active_task_id or not session.active_chat_id:
            return
        try:
            st = await self._api.get_status(session.active_task_id)
        except Exception:
            self._store.save(BotSession())
            return
        if st.is_running or (st.is_completed and not st.is_really_completed):
            self._last_state_for_diff = {}
            self._start_monitor(session.active_task_id, session.active_chat_id)
        else:
            self._store.save(BotSession())

    async def _handle_inbound(self, chat_id: str, msg_id: str, text: str) -> None:
        async with self._guard:
            session = self._store.load()
            if session.active_task_id:
                if session.expecting_input and session.active_chat_id == chat_id:
                    try:
                        await self._api.submit_input(session.active_task_id, text)
                        session.expecting_input = False
                        self._store.save(session)
                        await self._messenger.create_markdown(chat_id, "已收到输入，任务继续执行。")
                    except Exception:
                        await self._messenger.create_markdown(chat_id, "提交输入失败。")
                return

            try:
                running_tid = await self._api.any_running_task_id()
            except Exception:
                running_tid = None
            if running_tid:
                return

            try:
                task_id = await self._api.create_task(text)
            except Exception:
                await self._messenger.create_markdown(chat_id, "创建任务失败。")
                return

            state_card_id = await self._messenger.create_markdown(chat_id, f"已创建任务 `{task_id}`，开始执行。")
            session = BotSession(
                active_task_id=task_id,
                active_chat_id=chat_id,
                active_source_message_id=msg_id,
                state_card_message_id=state_card_id,
                expecting_input=False,
                last_pending_query_sent=None,
                last_state_hash=None,
            )
            self._store.save(session)
            self._last_state_for_diff = {}
            self._start_monitor(task_id, chat_id)

    def _start_monitor(self, task_id: str, chat_id: str) -> None:
        if self._monitor_task and not self._monitor_task.done():
            return
        self._monitor_task = asyncio.create_task(self._monitor(task_id, chat_id))

    async def _monitor(self, task_id: str, chat_id: str) -> None:
        while not self._stop_event.is_set():
            session = self._store.load()
            if session.active_task_id != task_id:
                return
            try:
                st = await self._api.get_status(task_id)
            except Exception:
                await self._finalize_session(task_id, failed=True)
                return

            if st.waiting_for_input:
                pending = (st.pending_query or "").strip()
                if pending and pending != (session.last_pending_query_sent or ""):
                    await self._messenger.create_markdown(chat_id, pending)
                    session.last_pending_query_sent = pending
                    session.expecting_input = True
                    self._store.save(session)

            try:
                new_state = await self._api.get_state(task_id)
            except Exception:
                new_state = None

            if new_state is not None:
                focused_state = _focus_state_for_push(new_state)
                state_hash = self._hash_state(focused_state)
                if state_hash != (session.last_state_hash or ""):
                    prev = self._last_state_for_diff if self._last_state_for_diff is not None else {}
                    max_changes = 200
                    changes = diff_json(prev, focused_state, max_changes=max_changes + 1)
                    truncated = len(changes) > max_changes
                    if truncated:
                        changes = changes[:max_changes]
                    if changes:
                        msg = self._render_state_updates(changes, focused_state, truncated=truncated)
                        await self._send_state_update(session, chat_id, msg)
                    session.last_state_hash = state_hash
                    self._store.save(session)
                    self._last_state_for_diff = focused_state

            if (not st.is_running) and st.is_completed:
                await self._finalize_session(task_id, failed=False)
                return
            await asyncio.sleep(self._poll_interval_s)

    async def _send_state_update(self, session: BotSession, chat_id: str, markdown: str) -> None:
        await self._messenger.create_markdown(chat_id, markdown)

    async def _finalize_session(self, task_id: str, failed: bool) -> None:
        session = self._store.load()
        if session.active_task_id != task_id:
            return
        final_text = "任务已结束。" if failed else "任务已完成。"
        if session.state_card_message_id:
            try:
                await self._messenger.patch_markdown(session.state_card_message_id, final_text)
                self._store.save(BotSession())
                return
            except Exception:
                pass
        if session.active_chat_id:
            try:
                await self._messenger.create_markdown(session.active_chat_id, final_text)
            except Exception:
                pass
        self._store.save(BotSession())
        
    @staticmethod
    def _hash_state(state: Dict[str, Any]) -> str:
        payload = json.dumps(state, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    @staticmethod
    def _render_state_updates(changes, state: Dict[str, Any], *, truncated: bool) -> str:
        lines = []
        for path, _old, _new in changes:
            v = _get_value_by_path(state, path)
            payload = json.dumps(v, ensure_ascii=False, indent=2)
            lines.append(f"- `{path}`\n```json\n{payload}\n```")
        if truncated:
            lines.append("- ...(仅展示前若干处变化)")
        return "\n".join(lines)


def load_bot_from_env(project_root: str) -> FeishuAutomasBot:
    app_id = os.environ.get("FEISHU_APP_ID", "").strip()
    app_secret = os.environ.get("FEISHU_APP_SECRET", "").strip()
    if not app_id or not app_secret:
        raise RuntimeError("missing FEISHU_APP_ID/FEISHU_APP_SECRET")
    api_base = os.environ.get("AUTOMAS_API_BASE", "http://127.0.0.1:8000").strip()
    poll_interval_s = float(os.environ.get("FEISHU_POLL_INTERVAL_SECONDS", "5").strip() or "5")
    session_path = os.environ.get("FEISHU_SESSION_PATH", os.path.join(project_root, "storage", "feishu_session.json"))
    return FeishuAutomasBot(
        app_id=app_id,
        app_secret=app_secret,
        automas_api_base=api_base,
        session_path=session_path,
        poll_interval_s=poll_interval_s,
    )
