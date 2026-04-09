import os
import sys
import base64
import mimetypes
import io
import urllib.parse
import urllib.request
from datetime import datetime


from config.logger import setup_logger

logger = setup_logger("FileOperation")

IMAGE_EXTS = {
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".bmp",
    ".tif",
    ".tiff",
    ".ico",
    ".svg",
}
MAX_IMAGE_BYTES = 10 * 1024 * 1024
MAX_DOWNLOAD_BYTES = 50 * 1024 * 1024
JPEG_MAX_EDGE = 4096
COMPRESS_TRIES = 7
JPEG_QUALITY_START = 85
JPEG_QUALITY_MIN = 35
JPEG_QUALITY_STEP = 10


def _is_http_url(value: str) -> bool:
    return isinstance(value, str) and value.startswith(("http://", "https://"))


def _is_image_resource(ext: str, mime_type: str | None) -> bool:
    return (mime_type or "").startswith("image/") or (ext or "").lower() in IMAGE_EXTS


def _text_payload(text: str) -> list:
    return [{"type": "text", "text": text}]


def _image_and_text_payload(image_url: str, text: str) -> list:
    return [
        {"type": "image_url", "image_url": {"url": image_url}},
        {"type": "text", "text": text},
    ]


def _base64_data_url(mime_type: str, raw: bytes) -> str:
    b64 = base64.b64encode(raw).decode("utf-8")
    return f"data:{mime_type};base64,{b64}"


def _base64_data_url_for_local_llm(mime_type: str, raw: bytes) -> str:
    b64 = base64.b64encode(raw).decode("utf-8")
    return f"data:{mime_type};base64,{b64},$BASE64_IMAGE"


def _ensure_pil_image():
    from PIL import Image
    return Image


def _prepare_pil_image(img, Image):
    if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
        rgba = img.convert("RGBA")
        bg = Image.new("RGBA", rgba.size, (255, 255, 255, 255))
        img = Image.alpha_composite(bg, rgba).convert("RGB")
    else:
        img = img.convert("RGB")
    w, h = img.size
    if max(w, h) > JPEG_MAX_EDGE:
        scale = JPEG_MAX_EDGE / max(w, h)
        nw = max(1, int(w * scale))
        nh = max(1, int(h * scale))
        img = img.resize((nw, nh), Image.Resampling.LANCZOS)
    return img


def _compress_pil_image_to_jpeg(img, Image) -> tuple[bytes | None, list[str], int | None, int | None]:
    quality = JPEG_QUALITY_START
    best_quality = None
    best_size = None

    for _ in range(COMPRESS_TRIES):
        buf = io.BytesIO()
        try:
            img.save(buf, format="JPEG", quality=quality, optimize=True, progressive=True)
        except Exception:
            img.save(buf, format="JPEG", quality=quality)
        data = buf.getvalue()

        if best_size is None or len(data) < best_size:
            best_size = len(data)
            best_quality = quality

        if len(data) <= MAX_IMAGE_BYTES:
            info_lines = [
                "压缩: 是",
                f"压缩后大小: {len(data)} bytes ({len(data) / 1024:.2f} KB)",
                f"输出格式: JPEG (quality={quality})",
                f"输出尺寸: {img.size[0]}x{img.size[1]}",
            ]
            return data, info_lines, best_quality, best_size

        ratio = (MAX_IMAGE_BYTES / max(1, len(data))) ** 0.5 * 0.95
        ratio = max(0.2, min(0.9, ratio))
        nw = max(1, int(img.size[0] * ratio))
        nh = max(1, int(img.size[1] * ratio))
        img = img.resize((nw, nh), Image.Resampling.LANCZOS)
        quality = max(JPEG_QUALITY_MIN, quality - JPEG_QUALITY_STEP)

    return None, [], best_quality, best_size


def _read_image_local(abs_path: str, mime_type: str | None) -> list:
    ext = os.path.splitext(abs_path)[1].lower()
    stat = os.stat(abs_path)
    created_at = datetime.fromtimestamp(os.path.getctime(abs_path)).strftime("%Y-%m-%d %H:%M:%S")
    original_size_bytes = stat.st_size
    original_size_kb = original_size_bytes / 1024
    filename = os.path.basename(abs_path)

    if original_size_bytes <= MAX_IMAGE_BYTES:
        with open(abs_path, "rb") as f:
            raw = f.read()
        send_mime = mime_type or "application/octet-stream"
        data_url = _base64_data_url_for_local_llm(send_mime, raw)
        logger.info(f"Successfully read image file: {abs_path} (mime={send_mime}, original={original_size_bytes} bytes, send={len(raw)} bytes)")
        text = (
            "图片内容已成功读取\n"
            f"文件名: {filename}\n"
            f"路径: {abs_path}\n"
            f"创建时间: {created_at}\n"
            f"原始大小: {original_size_bytes} bytes ({original_size_kb:.2f} KB)\n"
            "压缩: 否\n"
            f"MIME: {send_mime}"
        )
        return _image_and_text_payload(data_url, text)

    if ext == ".svg":
        return _text_payload(
            "读取图片失败：图片原始体积超过 10MB，且内置压缩对该格式支持有限，请将图片控制在 10MB 以内后重试。\n"
            f"文件名: {filename}\n"
            f"路径: {abs_path}\n"
            f"创建时间: {created_at}\n"
            f"原始大小: {original_size_bytes} bytes ({original_size_kb:.2f} KB)\n"
            f"限制: {MAX_IMAGE_BYTES} bytes (10.00 MB)\n"
            f"MIME: {mime_type or 'unknown'}"
        )

    try:
        Image = _ensure_pil_image()
    except Exception as e:
        return _text_payload(
            "读取图片失败：图片原始体积超过 10MB，但当前环境缺少可用的图片压缩能力，请将图片控制在 10MB 以内后重试。\n"
            f"文件名: {filename}\n"
            f"路径: {abs_path}\n"
            f"创建时间: {created_at}\n"
            f"原始大小: {original_size_bytes} bytes ({original_size_kb:.2f} KB)\n"
            f"限制: {MAX_IMAGE_BYTES} bytes (10.00 MB)\n"
            f"错误: {e}"
        )

    try:
        img = Image.open(abs_path)
        img.load()
    except Exception as e:
        return _text_payload(
            "读取图片失败：图片原始体积超过 10MB，且内置压缩无法打开该图片，请将图片控制在 10MB 以内后重试。\n"
            f"文件名: {filename}\n"
            f"路径: {abs_path}\n"
            f"创建时间: {created_at}\n"
            f"原始大小: {original_size_bytes} bytes ({original_size_kb:.2f} KB)\n"
            f"限制: {MAX_IMAGE_BYTES} bytes (10.00 MB)\n"
            f"错误: {e}"
        )

    img = _prepare_pil_image(img, Image)
    send_bytes, compress_info_lines, best_quality, best_size = _compress_pil_image_to_jpeg(img, Image)
    if send_bytes is None:
        return _text_payload(
            "读取图片失败：图片原始体积超过 10MB，且内置压缩效果有限，仍无法压缩到 10MB 以内，请将图片控制在 10MB 以内后重试。\n"
            f"文件名: {filename}\n"
            f"路径: {abs_path}\n"
            f"创建时间: {created_at}\n"
            f"原始大小: {original_size_bytes} bytes ({original_size_kb:.2f} KB)\n"
            f"最佳压缩结果: {best_size} bytes ({best_size / 1024:.2f} KB) (JPEG quality={best_quality})\n"
            f"限制: {MAX_IMAGE_BYTES} bytes (10.00 MB)\n"
            f"MIME: {mime_type or 'unknown'}"
        )

    send_mime = "image/jpeg"
    data_url = _base64_data_url_for_local_llm(send_mime, send_bytes)
    logger.info(
        f"Successfully read image file: {abs_path} (mime={send_mime}, original={original_size_bytes} bytes, send={len(send_bytes)} bytes)"
    )
    text = (
        "图片内容已成功读取\n"
        f"文件名: {filename}\n"
        f"路径: {abs_path}\n"
        f"创建时间: {created_at}\n"
        f"原始大小: {original_size_bytes} bytes ({original_size_kb:.2f} KB)\n"
        + "\n".join(compress_info_lines)
        + "\n"
        f"MIME: {send_mime}"
    )
    return _image_and_text_payload(data_url, text)


def _head_url(url: str) -> tuple[str | None, int | None, str | None, str | None]:
    head_mime = None
    content_length = None
    last_modified = None
    head_error = None

    try:
        req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "automas/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            ct = (resp.headers.get("Content-Type") or "").split(";", 1)[0].strip().lower()
            head_mime = ct or None
            cl = (resp.headers.get("Content-Length") or "").strip()
            if cl.isdigit():
                content_length = int(cl)
            last_modified = (resp.headers.get("Last-Modified") or "").strip() or None
    except Exception as e:
        head_error = str(e)

    return head_mime, content_length, last_modified, head_error


def _download_url(url: str, limit_bytes: int) -> tuple[bytes | None, str | None]:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "automas/1.0"})
        with urllib.request.urlopen(req, timeout=20) as resp:
            raw = resp.read(limit_bytes + 1)
        if len(raw) > limit_bytes:
            return None, "download_limit_exceeded"
        return raw, None
    except Exception as e:
        return None, str(e)


def _read_image_url(url: str) -> list:
    parsed = urllib.parse.urlparse(url)
    url_path = parsed.path or ""
    filename = os.path.basename(url_path) or url
    ext = os.path.splitext(url_path)[1].lower()

    head_mime, content_length, last_modified, head_error = _head_url(url)
    is_image_url = _is_image_resource(ext, head_mime)

    if not is_image_url:
        return _text_payload(
            "读取图片失败：传入的是 URL，但该 URL 看起来不是图片资源。\n"
            f"URL: {url}\n"
            f"文件名: {filename}\n"
            f"扩展名: {ext or 'unknown'}\n"
            f"Content-Type: {head_mime or 'unknown'}\n"
            + (f"HEAD 错误: {head_error}\n" if head_error else "")
            + "请传入图片文件路径或公网可访问的图片 URL。"
        )

    if content_length is not None and content_length > MAX_IMAGE_BYTES:
        if ext == ".svg" or head_mime == "image/svg+xml":
            return _text_payload(
                "读取图片失败：图片原始体积超过 10MB，且内置压缩对该格式支持有限，请将图片控制在 10MB 以内后重试。\n"
                f"URL: {url}\n"
                f"文件名: {filename}\n"
                f"Last-Modified: {last_modified or 'unknown'}\n"
                f"原始大小: {content_length} bytes ({content_length / 1024:.2f} KB)\n"
                f"限制: {MAX_IMAGE_BYTES} bytes (10.00 MB)\n"
                f"MIME: {head_mime or 'unknown'}"
            )

        try:
            Image = _ensure_pil_image()
        except Exception as e:
            return _text_payload(
                "读取图片失败：图片原始体积超过 10MB，但当前环境缺少可用的图片压缩能力，请将图片控制在 10MB 以内后重试。\n"
                f"URL: {url}\n"
                f"文件名: {filename}\n"
                f"Last-Modified: {last_modified or 'unknown'}\n"
                f"原始大小: {content_length} bytes ({content_length / 1024:.2f} KB)\n"
                f"限制: {MAX_IMAGE_BYTES} bytes (10.00 MB)\n"
                f"错误: {e}"
            )

        raw, download_error = _download_url(url, MAX_DOWNLOAD_BYTES)
        if raw is None:
            if download_error == "download_limit_exceeded":
                return _text_payload(
                    "读取图片失败：远程图片体积过大，超出内置下载与压缩处理上限，请将图片控制在 10MB 以内后重试。\n"
                    f"URL: {url}\n"
                    f"文件名: {filename}\n"
                    f"Last-Modified: {last_modified or 'unknown'}\n"
                    f"原始大小(HEAD): {content_length} bytes ({content_length / 1024:.2f} KB)\n"
                    f"下载上限: {MAX_DOWNLOAD_BYTES} bytes\n"
                    f"限制: {MAX_IMAGE_BYTES} bytes (10.00 MB)\n"
                    f"MIME: {head_mime or 'unknown'}"
                )
            return _text_payload(
                "读取图片失败：图片原始体积超过 10MB，需要下载后压缩，但下载失败，请将图片控制在 10MB 以内后重试。\n"
                f"URL: {url}\n"
                f"文件名: {filename}\n"
                f"Last-Modified: {last_modified or 'unknown'}\n"
                f"原始大小: {content_length} bytes ({content_length / 1024:.2f} KB)\n"
                f"限制: {MAX_IMAGE_BYTES} bytes (10.00 MB)\n"
                f"错误: {download_error}"
            )

        try:
            img = Image.open(io.BytesIO(raw))
            img.load()
        except Exception as e:
            return _text_payload(
                "读取图片失败：图片原始体积超过 10MB，且内置压缩无法打开该图片，请将图片控制在 10MB 以内后重试。\n"
                f"URL: {url}\n"
                f"文件名: {filename}\n"
                f"Last-Modified: {last_modified or 'unknown'}\n"
                f"原始大小(HEAD): {content_length} bytes ({content_length / 1024:.2f} KB)\n"
                f"限制: {MAX_IMAGE_BYTES} bytes (10.00 MB)\n"
                f"错误: {e}"
            )

        img = _prepare_pil_image(img, Image)
        send_bytes, compress_info_lines, best_quality, best_size = _compress_pil_image_to_jpeg(img, Image)
        if send_bytes is None:
            return _text_payload(
                "读取图片失败：图片原始体积超过 10MB，且内置压缩效果有限，仍无法压缩到 10MB 以内，请将图片控制在 10MB 以内后重试。\n"
                f"URL: {url}\n"
                f"文件名: {filename}\n"
                f"Last-Modified: {last_modified or 'unknown'}\n"
                f"原始大小(HEAD): {content_length} bytes ({content_length / 1024:.2f} KB)\n"
                f"最佳压缩结果: {best_size} bytes ({best_size / 1024:.2f} KB) (JPEG quality={best_quality})\n"
                f"限制: {MAX_IMAGE_BYTES} bytes (10.00 MB)\n"
                f"MIME: {head_mime or 'unknown'}"
            )

        send_mime = "image/jpeg"
        data_url = _base64_data_url(send_mime, send_bytes)
        text = (
            "图片内容已成功读取\n"
            f"文件名: {filename}\n"
            f"URL: {url}\n"
            f"Last-Modified: {last_modified or 'unknown'}\n"
            f"原始大小(HEAD): {content_length} bytes ({content_length / 1024:.2f} KB)\n"
            + "\n".join(compress_info_lines)
            + "\n"
            f"MIME: {send_mime}"
        )
        return _image_and_text_payload(data_url, text)

    size_line = (
        f"原始大小(HEAD): {content_length} bytes ({content_length / 1024:.2f} KB)\n"
        if content_length is not None
        else "原始大小(HEAD): unknown\n"
    )
    warn_line = (
        "提示: 未能从服务器获取 Content-Length，请确保图片本体 ≤ 10MB，否则模型端可能拒绝。\n"
        if content_length is None
        else ""
    )
    head_line = (f"提示: HEAD 获取失败: {head_error}\n" if head_error else "")

    text = (
        "图片内容已成功读取\n"
        f"文件名: {filename}\n"
        f"URL: {url}\n"
        f"Last-Modified: {last_modified or 'unknown'}\n"
        + size_line
        + "压缩: 否\n"
        + f"MIME: {head_mime or 'unknown'}\n"
        + head_line
        + warn_line
    )
    return _image_and_text_payload(url, text)


def read_file(file_path):
    """
    Reads the content of a file.
    
    Args:
        file_path (str): The path to the file to read.
        
    Returns:
        str | list: 普通文本等可读文件返回内容字符串（失败时返回错误字符串）；图片文件返回多模态 payload 列表（必要时仅返回 text 的列表用于报错）。
        
    Raises:
        FileNotFoundError: If the file does not exist.
        IOError: If there is an error reading the file.
    """
    logger.info(f"Reading file: {file_path}")
    try:
        if _is_http_url(file_path):
            return _read_image_url(file_path)

        abs_path = os.path.abspath(file_path)
        mime_type, _ = mimetypes.guess_type(abs_path)
        ext = os.path.splitext(abs_path)[1].lower()
        if _is_image_resource(ext, mime_type):
            return _read_image_local(abs_path, mime_type)

        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            logger.info(f"Successfully read {len(content)} characters from {file_path}")
            return content
    except Exception as e:
        error_msg = f"Error reading file {file_path}: {e}"
        logger.error(error_msg)
        return error_msg

def write_file(file_path, content, mode: str = "write"):
    """
    Writes content to a file. Creates directories if they don't exist.
    
    Args:
        file_path (str): The path to the file to write.
        content (str): The content to write to the file.
        mode (str): write or append.
        
    Returns:
        str: Success message or error message.
    """
    file_mode = "a" if mode == "append" else "w"
    logger.info(f"Writing to file: {file_path} (mode={mode})")
    try:
        # Create directory if it doesn't exist
        directory = os.path.dirname(file_path)
        if directory and not os.path.exists(directory):
            logger.info(f"Creating directory: {directory}")
            os.makedirs(directory)
            
        with open(file_path, file_mode, encoding='utf-8') as f:
            f.write(content)
            
        success_msg = f"Successfully wrote to {file_path}" if file_mode == "w" else f"Successfully appended to {file_path}"
        logger.info(success_msg)
        return success_msg
    except Exception as e:
        error_msg = f"Error writing to file {file_path}: {e}"
        logger.error(error_msg)
        return error_msg

def load_full_skill_description(file_path):
    """
    Reads the content of a skills.md file.
    
    Args:
        file_path (str): The path to the skills.md file.
        
    Returns:
        str: The content of the file.
    """
    logger.info(f"Loading skill doc: {file_path}")
    print(f"Loading skill doc: {file_path}")
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            logger.info(f"Successfully read skill.md {len(content)} characters from {file_path}")
            print(f"Successfully read skill.md {len(content)} characters from {file_path}")
            return content
    except Exception as e:
        error_msg = f"Error reading skill {file_path}: {e}"
        logger.error(error_msg)
        return error_msg

# if __name__ == "__main__":
#     # Test cases
#     test_file = "test_output/test.txt"
#     print(write_file(test_file, "Hello, World!"))
#     print(read_file(test_file))
