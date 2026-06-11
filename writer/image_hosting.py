"""将文章中的本地图片路径替换为 GitHub raw CDN URL。

使用前提：项目已推送到 GitHub，output/images/ 已在仓库中。
raw URL 格式：
  https://raw.githubusercontent.com/用户/仓库/main/output/images/xxx.jpeg
"""

import re
from pathlib import Path

from config.settings import settings
from utils.logger import get_logger

logger = get_logger(__name__)


def replace_local_paths_in_md(filepath: Path) -> int:
    """扫描 md 中的本地图片路径，替换为 GitHub raw URL。"""
    repo = settings.github_image_repo
    if not repo:
        return 0

    project_root = Path(__file__).parent.parent
    branch = "main"
    content = filepath.read_text(encoding="utf-8")
    local_paths = _find_local_paths(content)
    if not local_paths:
        return 0

    replaced = 0
    for local_path in local_paths:
        fp = Path(local_path)
        try:
            relative = fp.relative_to(project_root)
        except ValueError:
            continue
        url = f"https://raw.githubusercontent.com/{repo}/{branch}/{relative.as_posix()}"
        content = content.replace(local_path, url)
        replaced += 1
        logger.info(f"替换: {fp.name} → raw.githubusercontent.com")

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
