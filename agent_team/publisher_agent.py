"""图片生成 Agent：为写好的文章生成封面图和配图。"""

import re
from pathlib import Path

from agent_team.base_agent import BaseAgent
from agent_team.database import get_written_articles, get_pending_sets, update_set_status

try:
    from writer.image_generator import generate_cover, generate_illustrations
    HAS_XYQ = True
except ImportError:
    HAS_XYQ = False

try:
    from writer.image_hosting import replace_local_paths_in_md
    HAS_HOSTING = True
except ImportError:
    HAS_HOSTING = False


class PublisherAgent(BaseAgent):
    """图片生成 Agent。为已完成文章生成封面图和配图，不生成发布指令。"""

    name = "publisher"

    def run_once(self) -> int:
        written_sets = get_pending_sets("written")
        if not written_sets:
            return 0

        total = 0
        for s in written_sets:
            set_id = s["id"]
            articles = get_written_articles(set_id)
            output_dir = Path(__file__).parent.parent / "output"
            images_dir = output_dir / "images"
            images_dir.mkdir(parents=True, exist_ok=True)

            for article in articles:
                filepath = Path(article["filepath"])
                if not filepath.exists():
                    self.logger.warning(f"文章文件不存在: {filepath}")
                    continue

                try:
                    if HAS_XYQ:
                        self._generate_article_images(filepath, images_dir)
                    total += 1
                except Exception as e:
                    self.logger.error(f"图片生成失败 {filepath}: {e}")

            update_set_status(set_id, "published")

        return total

    def _generate_article_images(self, filepath: Path, images_dir: Path):
        """为文章生成封面图和配图，更新文章文件。"""
        content = filepath.read_text(encoding="utf-8")

        # 提取标题和摘要
        title = self._extract_fm_value(content, "title") or filepath.stem
        summary = self._extract_fm_value(content, "summary") or ""

        # 已有封面图就不重复生成
        cover = self._extract_fm_value(content, "cover") or ""
        if not cover or cover == "使用科技类相关官方配图或 AI 生成封面图":
            self.logger.info(f"生成封面图: {title}")
            # 用日期作前缀避免覆盖
            date_prefix = filepath.stem.split("_")[0] if "_" in filepath.stem else filepath.stem
            cover_path = generate_cover(title, summary, str(images_dir), prefix=f"cover_{date_prefix}")
            if cover_path:
                self._update_front_matter(filepath, "cover", str(cover_path))

        # 生成配图（跳过已有配图的文章）
        body = self._extract_body(content)
        if body and "![文章配图]" not in content:
            self.logger.info(f"生成配图: {title}")
            date_prefix = filepath.stem.split("_")[0] if "_" in filepath.stem else filepath.stem
            illustrations = generate_illustrations(body, str(images_dir), count=2, prefix=f"ill_{date_prefix}")
            if illustrations:
                self._embed_illustrations(filepath, illustrations)

        # 将本地图片路径替换为 GitHub raw CDN URL
        if HAS_HOSTING:
            replaced = replace_local_paths_in_md(filepath)
            if replaced:
                self.logger.info(f"已替换 {replaced} 张图片为 raw URL")

    def _extract_fm_value(self, content: str, key: str) -> str:
        """从 Front Matter 中提取指定字段的值。"""
        m = re.match(r"^---\s*\n(.*?)\n---", content, re.DOTALL)
        if not m:
            return ""
        for line in m.group(1).split("\n"):
            if line.startswith(f"{key}:"):
                val = line.split(":", 1)[1].strip().strip('"').strip("'")
                return val
        return ""

    def _update_front_matter(self, filepath: Path, key: str, value: str):
        """更新文章 Front Matter 中的字段。"""
        content = filepath.read_text(encoding="utf-8")
        m = re.match(r"^---\s*\n(.*?)\n---", content, re.DOTALL)
        if not m:
            return
        fm_text = m.group(1)
        lines = fm_text.split("\n")
        updated = False
        for i, line in enumerate(lines):
            if line.startswith(f"{key}:"):
                lines[i] = f'{key}: "{value}"'
                updated = True
                break
        if not updated:
            lines.append(f'{key}: "{value}"')
        new_fm = "---\n" + "\n".join(lines) + "\n---"
        new_content = content[:m.start()] + new_fm + content[m.end():]
        filepath.write_text(new_content, encoding="utf-8")
        self.logger.info(f"已更新 {key}: {value}")

    def _extract_body(self, content: str) -> str:
        """提取文章正文（去掉 Front Matter 和元信息章节）。"""
        body = re.sub(r"^---\s*\n.*?\n---\s*\n?", "", content, count=1, flags=re.DOTALL)
        meta_keywords = {"标题候选", "推荐标题", "摘要", "话题建议", "配图建议", "来源清单", "参考来源"}

        def is_meta(line: str) -> bool:
            stripped = line.strip()
            if not stripped.startswith("#"):
                return False
            text = stripped.lstrip("#").strip()
            return text in meta_keywords or any(text.startswith(m) or m.startswith(text) for m in meta_keywords)

        lines = body.split("\n")
        clean = []
        for line in lines:
            if is_meta(line):
                break
            clean.append(line)
        return "\n".join(clean).strip()

    def _embed_illustrations(self, filepath: Path, illustrations: list[str]):
        """在正文中插入配图。"""
        content = filepath.read_text(encoding="utf-8")
        body_start = self._find_body_start(content)
        if body_start < 0:
            return
        lines = content.split("\n")
        inserted = 0
        for i, path in enumerate(illustrations):
            # 在正文第二个段落后插入
            insert_at = body_start
            para_count = 0
            for j in range(body_start, len(lines)):
                if lines[j].strip() and not lines[j].startswith("#"):
                    para_count += 1
                    if para_count == 2 * (i + 1):
                        insert_at = j + 1
                        break
            img_tag = f"\n![文章配图]({path})\n"
            lines.insert(insert_at, img_tag)
            inserted += 1
        filepath.write_text("\n".join(lines), encoding="utf-8")
        self.logger.info(f"已嵌入 {inserted} 张配图")

    def _find_body_start(self, content: str) -> int:
        """找到正文起始行号。"""
        lines = content.split("\n")
        meta_keywords = {"标题候选", "推荐标题", "摘要", "话题建议", "配图建议"}

        def is_meta(line: str) -> bool:
            stripped = line.strip()
            if not stripped.startswith("#"):
                return False
            text = stripped.lstrip("#").strip()
            return text in meta_keywords or any(text.startswith(m) or m.startswith(text) for m in meta_keywords)

        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith("#") and not is_meta(line):
                return i
        # Fallback: 找 Front Matter 结束后的第一个非空行
        for i, line in enumerate(lines):
            if line.strip() == "---" and i > 0:
                return i + 1
        return 0
