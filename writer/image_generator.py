"""小云雀 (xyq) 图片生成器：为文章生成封面图和配图。"""

import json
import os
import subprocess
import sys
import time
from pathlib import Path

from utils.logger import get_logger

logger = get_logger(__name__)

XYQ_SCRIPTS_DIR = Path(os.path.expanduser("~/.agents/skills/xyq-nest-skill/scripts"))


def _ensure_env():
    """确保 XYQ_ACCESS_KEY 在环境中可用，从 .env 读取。"""
    if "XYQ_ACCESS_KEY" in os.environ and os.environ["XYQ_ACCESS_KEY"]:
        return
    # 从 .env 文件读取
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("XYQ_ACCESS_KEY="):
                val = line.split("=", 1)[1].strip().strip('"').strip("'")
                if val:
                    os.environ["XYQ_ACCESS_KEY"] = val
                    return
    logger.warning("XYQ_ACCESS_KEY 未配置，图片生成功能不可用")


def _run_script(script_name: str, *args, timeout: int = 120) -> dict:
    """运行 xyq 脚本并解析 JSON 输出。"""
    _ensure_env()
    script_path = XYQ_SCRIPTS_DIR / script_name
    if not script_path.exists():
        raise FileNotFoundError(f"xyq 脚本不存在: {script_path}")

    result = subprocess.run(
        [sys.executable, str(script_path), *args],
        capture_output=True, text=False, timeout=timeout,
    )
    if result.returncode != 0:
        stderr = result.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(f"xyq 脚本失败 ({script_name}): {stderr}")
    return _parse_json_output(result.stdout.decode("utf-8", errors="replace"))


def _parse_json_output(stdout: str) -> dict:
    """从脚本输出中提取 JSON，忽略非 JSON 前缀文本。"""
    for i, ch in enumerate(stdout):
        if ch in ("{", "["):
            try:
                return json.loads(stdout[i:])
            except json.JSONDecodeError:
                break
    return json.loads(stdout) if stdout.strip() else {}


def _extract_urls(get_thread_result: dict) -> list[str]:
    """从 get_thread 结果中提取产物 URL。"""
    urls = []
    for msg in get_thread_result.get("messages", []):
        content = msg.get("content")
        if not isinstance(content, list):
            continue
        for item in content:
            if not isinstance(item, dict):
                continue
            if item.get("sub_type") == "biz/x_data_image":
                data_str = item.get("data", "")
                if isinstance(data_str, str):
                    try:
                        data = json.loads(data_str)
                        img = data.get("image", {})
                        url = img.get("url", "")
                        if url and url.startswith("http"):
                            urls.append(url)
                    except json.JSONDecodeError:
                        pass
            # 也可能直接有 url 字段
            url = item.get("url", "")
            if url and isinstance(url, str) and url.startswith("http"):
                urls.append(url)
    # 去重
    seen = set()
    return [u for u in urls if not (u in seen or seen.add(u))]


def submit_and_poll(prompt: str, timeout: int = 180) -> list[str]:
    """提交图片生成任务并轮询直到完成，返回产物 URL 列表。"""
    task = _run_script("submit_run.py", "--message", prompt)
    thread_id = task.get("thread_id", "")
    run_id = task.get("run_id", "")
    web_link = task.get("web_thread_link", "")
    logger.info(f"xyq 任务已提交: {web_link or thread_id}")

    if not thread_id or not run_id:
        raise RuntimeError(f"xyq 返回不完整: {task}")

    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            result = _run_script(
                "get_thread.py",
                "--thread-id", thread_id,
                "--run-id", run_id,
                "--after-seq", "0",
                timeout=30,
            )
            urls = _extract_urls(result)
            if urls:
                logger.info(f"xyq 任务完成，获取到 {len(urls)} 个产物")
                return urls
        except RuntimeError as e:
            # 检查是否是"进行中"状态的预期行为
            logger.debug(f"轮询中: {e}")

        time.sleep(10)

    logger.warning(f"xyq 任务超时 (>{timeout}s), thread_id={thread_id}")
    return []


def download_images(urls: list[str], output_dir: str, prefix: str) -> list[str]:
    """下载图片到本地，返回本地文件路径列表（自动修正 .image 后缀为 .jpeg）。"""
    if not urls:
        return []

    result = _run_script(
        "download_results.py",
        "--urls", *urls,
        "--output-dir", output_dir,
        "--prefix", prefix,
        timeout=300,
    )
    files = result.get("downloaded", [])
    # 修正后缀： .image → .jpeg（xyq 的 .image 文件实际是 JPEG）
    fixed = []
    for f in files:
        fp = Path(f)
        if fp.suffix.lower() == ".image":
            new_fp = fp.with_suffix(".jpeg")
            if fp.exists():
                # 始终用新文件覆盖旧 .jpeg
                if new_fp.exists():
                    new_fp.unlink()
                fp.rename(new_fp)
            fixed.append(str(new_fp))
        else:
            fixed.append(f)
    return fixed


def generate_cover(title: str, summary: str, output_dir: str, prefix: str = "cover") -> str | None:
    """为文章生成封面图，返回本地路径或 None。"""
    prompt = f"生成一张科技文章封面图，主题是：{title}。{summary[:150]}"
    try:
        urls = submit_and_poll(prompt, timeout=180)
        if urls:
            files = download_images(urls, output_dir, prefix)
            if files:
                logger.info(f"封面图已生成: {files[0]}")
                return files[0]
    except Exception as e:
        logger.warning(f"生成封面图失败: {e}")
    return None


def generate_illustrations(body: str, output_dir: str, count: int = 2, prefix: str = "illustration") -> list[str]:
    """为文章生成配图，返回本地路径列表。"""
    paragraphs = [p.strip() for p in body.split("\n") if p.strip() and len(p) > 80]
    images = []
    for i in range(min(count, len(paragraphs))):
        para = paragraphs[i].lstrip("#").strip()[:100]
        prompt = f"生成一张科技文章配图，配合这段文字：{para}"
        try:
            urls = submit_and_poll(prompt, timeout=180)
            if urls:
                files = download_images(urls, output_dir, f"{prefix}_{i+1}")
                if files:
                    images.append(files[0])
        except Exception as e:
            logger.warning(f"生成配图 {i+1} 失败: {e}")
    return images
