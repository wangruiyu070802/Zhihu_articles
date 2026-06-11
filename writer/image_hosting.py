"""将文章中的本地图片路径替换为 jsDelivr CDN URL。

jsDelivr 在國內有 CDN 节点，知乎可以正常加载。
URL 格式：
  https://cdn.jsdelivr.net/gh/用户/仓库@main/output/images/xxx.jpeg
"""

import re
from pathlib import Path

from config.settings import settings
from utils.logger import get_logger

logger = get_logger(__name__)


def replace_local_paths_in_md(filepath: Path) -> int:
    """扫描 md 中的图片路径，替换为 jsDelivr CDN URL。

    同时处理两种场景：
    - 本地路径 → jsDelivr（首次运行）
    - raw.githubusercontent.com → jsDelivr（迁移场景）
    """
    repo = settings.github_image_repo
    if not repo:
        return 0

    project_root = Path(__file__).parent.parent
    branch = "main"
    content = filepath.read_text(encoding="utf-8")

    # 1. 替换本地路径
    local_paths = _find_local_paths(content)
    replaced = 0
    for local_path in local_paths:
        fp = Path(local_path)
        try:
            relative = fp.relative_to(project_root)
        except ValueError:
            continue
        url = f"https://cdn.jsdelivr.net/gh/{repo}@{branch}/{relative.as_posix()}"
        content = content.replace(local_path, url)
        replaced += 1

    # 2. 迁移旧的 raw.githubusercontent.com URL
    old_url = f"https://raw.githubusercontent.com/{repo}/{branch}/"
    new_url = f"https://cdn.jsdelivr.net/gh/{repo}@{branch}/"
    migrated_count = content.count(old_url)
    if migrated_count:
        content = content.replace(old_url, new_url)
        replaced += migrated_count

    if replaced:
        filepath.write_text(content, encoding="utf-8")
        logger.info(f"已更新 {filepath.name}，替换 {replaced} 张图片")
    return replaced


def _find_local_paths(content: str) -> list[str]:
    """找出 md 中所有本地图片路径。"""
    paths = set()
    for m in re.finditer(r"!\[.*?\]\((.+?)\)", content):
        p = m.group(1).strip()
        if p and not p.startswith("http"):
            paths.add(p)
    for m in re.finditer(r'cover:\s*"(.+?)"', content):
        p = m.group(1).strip()
        if p and not p.startswith("http"):
            paths.add(p)
    return list(paths)
