import json
import os
import ssl
import sys

import lark_oapi as lark
from lark_oapi import LogLevel
from lark_oapi.event.dispatcher_handler import EventDispatcherHandler


def _parse_text(message_content_json: str) -> str:
    try:
        content = json.loads(message_content_json)
    except Exception:
        return ""
    if isinstance(content, dict) and "text" in content:
        return str(content.get("text") or "").strip()
    if isinstance(content, dict) and "content" in content and isinstance(content.get("content"), list):
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
        return "\n\n".join(paragraphs).strip()
    return ""


def _on_message(event) -> None:
    try:
        message = event.event.message
        chat_id = message.chat_id
        msg_id = message.message_id
        text = _parse_text(message.content)
        if not text:
            return
        print(f"chat_id={chat_id} message_id={msg_id} text={text}")
        sys.stdout.flush()
    except Exception as exc:
        print(f"parse_error={exc}")
        sys.stdout.flush()


def main() -> None:
    https_verify = os.environ.get("PYTHONHTTPSVERIFY", "").strip()
    if https_verify == "0":
        import lark_oapi.ws.client as lark_ws_client

        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        orig_connect = lark_ws_client.websockets.connect

        def connect_wrapper(*args, **kwargs):
            kwargs.setdefault("ssl", ctx)
            return orig_connect(*args, **kwargs)

        lark_ws_client.websockets.connect = connect_wrapper

        orig_post = lark_ws_client.requests.post

        def post_wrapper(*args, **kwargs):
            kwargs.setdefault("verify", False)
            return orig_post(*args, **kwargs)

        lark_ws_client.requests.post = post_wrapper
    app_id = os.environ.get("FEISHU_APP_ID", "").strip()
    app_secret = os.environ.get("FEISHU_APP_SECRET", "").strip()
    if not app_id or not app_secret:
        raise SystemExit("missing FEISHU_APP_ID/FEISHU_APP_SECRET")
    dispatcher = (
        EventDispatcherHandler.builder(app_id, app_secret, LogLevel.INFO)
        .register_p2_im_message_receive_v1(_on_message)
        .build()
    )
    ws_client = lark.ws.Client(app_id, app_secret, event_handler=dispatcher)
    ws_client.start()


if __name__ == "__main__":
    main()
