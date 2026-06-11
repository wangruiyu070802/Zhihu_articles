"""文章生成器：筛选素材 -> 判断方向 -> 生成文章。"""

import re
from datetime import datetime
from pathlib import Path

from collector.base import Article
from config.settings import settings
from utils.logger import get_logger
from writer import prompts
from writer.ai_client import chat

logger = get_logger(__name__)


def format_articles_for_prompt(articles: list[Article]) -> str:
    parts = []
    for i, a in enumerate(articles, 1):
        parts.append(
            f"[{i}] {a.title}\n"
            f"    来源: {a.source_name}\n"
            f"    链接: {a.url}\n"
            f"    摘要: {a.summary[:500]}\n"
        )
    return "\n".join(parts)


def screen_articles(articles: list[Article]) -> str:
    logger.info(f"开始筛选 {len(articles)} 条素材...")
    formatted = format_articles_for_prompt(articles)
    result = chat([
        {"role": "system", "content": prompts.SYSTEM_SCREENING},
        {"role": "user", "content": prompts.PROMPT_SCREENING.format(articles=formatted)},
    ], temperature=0.3)
    return result


def write_article(articles: list[Article], style: str = "解读") -> str:
    formatted = format_articles_for_prompt(articles)
    formatted_text = (
        prompts.build_opportunity_prompt(formatted) if style == "机会拆解"
        else prompts.build_write_article_prompt(formatted)
    )
    logger.info(f"开始撰写{style}文章...")
    article = chat([
        {"role": "system", "content": prompts.SYSTEM_ARTICLES + prompts.SYSTEM_ARTICLES_VARIETY},
        {"role": "user", "content": formatted_text},
    ], temperature=0.8)
    return article


def write_memo(articles: list[Article]) -> str:
    formatted = format_articles_for_prompt(articles)
    memo = chat([
        {"role": "system", "content": prompts.SYSTEM_SCREENING},
        {"role": "user", "content": prompts.PROMPT_MEMO.format(articles=formatted)},
    ], temperature=0.3)
    return memo


def _get_heading_text(line: str) -> str:
    """提取标题文本，无论 # 级别。"""
    stripped = line.strip()
    if not stripped.startswith("#"):
        return ""
    return stripped.lstrip("#").strip()


META_NAMES = {"标题候选", "推荐标题", "摘要", "正文", "话题建议", "配图建议", "来源清单", "参考来源", "发布前检查清单", "发布前检查"}


def _is_meta_name(text: str) -> bool:
    """判断是否为元信息章节名称。"""
    return any(text == m or text.startswith(m) or m.startswith(text) for m in META_NAMES)


def _extract_title_from_content(content: str) -> str:
    """从 AI 输出中提取标题，过滤元信息章节名。"""
    for pattern in [
        r"## 推荐标题\s*\n(.+)",
        r"# 推荐标题\s*\n(.+)",
        r"## 标题候选.*?\n\d+\.\s*(.+)",
        r"# 标题候选.*?\n\d+\.\s*(.+)",
        r"^#\s+(.+)$",
    ]:
        m = re.search(pattern, content, re.DOTALL if "标题候选" in pattern else 0)
        if m:
            title = m.group(1).strip().strip("*").strip('"').strip("「").strip()
            # 跳过元信息章节名作为标题
            if title and not _is_meta_name(title):
                return title
    return ""


def _extract_front_matter(content: str, style: str) -> str:
    """从 AI 输出中提取信息，生成 YAML Front Matter。"""
    title = _extract_title_from_content(content)
    if not title:
        title = "科技前沿动态"
    summary = ""
    in_sum = False
    for line in content.split("\n"):
        if re.match(r"##\s*摘要", line):
            in_sum = True
            continue
        if in_sum:
            s = line.strip().strip("「」\"").strip()
            if s and not s.startswith("##"):
                if not any(kw in s[:20] for kw in ["好的", "没问题", "作为一名", "根据", "基于"]):
                    summary = s[:120]
                    break
    if not summary or len(summary) < 10:
        for line in content.split("\n"):
            s = line.strip()
            if len(s) > 30 and not s.startswith("#") and not s.startswith("["):
                summary = s[:120]
                break

    # 话题
    topics = []
    in_topic = False
    for line in content.split("\n"):
        if "话题建议" in line:
            in_topic = True
            continue
        if in_topic:
            if line.startswith("##"):
                break
            found = re.findall(r"#([^#\s]{2,30})", line)
            for t in found:
                clean_t = t.strip()
                if clean_t and clean_t not in topics:
                    topics.append(clean_t)
    if not topics:
        topics = ["人工智能", "科技前沿"]

    # 封面建议
    cover = ""
    in_cover = False
    for line in content.split("\n"):
        if "封面" in line and ("建议" in line or "图" in line):
            in_cover = True
            continue
        if in_cover:
            if line.startswith("##"):
                break
            s = line.strip().strip("- ").strip("1. ").strip()
            if s and len(s) > 5 and "封面" not in s:
                cover = s
                break
    if not cover:
        for line in content.split("\n"):
            if "封" in line and "图" in line and ("建议" in line or "使用" in line or "AI" in line):
                s = line.strip().lstrip("- ").lstrip("1. ").strip()
                if s and not s.startswith("##"):
                    cover = s
                    break
    if not cover:
        cover = "使用科技类相关官方配图或 AI 生成封面图"

    lines = ["---"]
    lines.append(f'title: "{title}"')
    lines.append(f'summary: "{summary}"')
    lines.append("topics:")
    for t in topics[:5]:
        lines.append(f"  - {t}")
    if cover:
        lines.append(f'cover: "{cover}"')
    lines.append("ai_generated: true")
    lines.append("allow_gifts: false")
    lines.append('content_source: "科技媒体综合整理"')
    lines.append("publish_mode: draft")
    lines.append("---")
    return "\n".join(lines)


def _clean_body(content: str) -> str:
    """去掉 AI 输出中的元信息区，只保留正文。"""
    lines = content.split("\n")

    def is_meta_heading(text: str) -> bool:
        return any(text == m or text.startswith(m) or m.startswith(text) for m in META_NAMES)

    # 找到第一个非元信息的 ## 章节作为正文起点
    body_start = None
    for i, line in enumerate(lines):
        heading = _get_heading_text(line)
        if heading:
            heading_level = len(line) - len(line.lstrip("#"))
            if heading_level >= 2 and not is_meta_heading(heading):
                body_start = i
                break

    if body_start is None:
        for i, line in enumerate(lines):
            heading = _get_heading_text(line)
            if heading and not is_meta_heading(heading):
                body_start = i
                break
    if body_start is None:
        body_start = 0

    # 找到正文结束位置（遇到下一个元信息章节前，不限 # 级别）
    body_end = len(lines)
    for i in range(body_start + 1, len(lines)):
        heading = _get_heading_text(lines[i])
        if heading and is_meta_heading(heading):
            body_end = i
            break

    body = "\n".join(lines[body_start:body_end]).strip()
    # 如果正文为空，尝试用去掉 Front Matter 后的全部内容
    if not body:
        body = re.sub(r"^---\s*\n.*?\n---\s*\n?", "", content, count=1, flags=re.DOTALL).strip()
    return body or content


def _extract_references(content: str) -> str:
    """提取参考来源部分。"""
    lines = content.split("\n")
    in_ref = False
    ref_lines = []
    for line in lines:
        if "来源清单" in line or "参考来源" in line:
            in_ref = True
            continue
        if in_ref:
            if line.strip().startswith("#"):
                break
            if line.strip():
                ref_lines.append(line.strip())
    return "\n".join(ref_lines) if ref_lines else ""


def save_article(content: str, style: str = "解读") -> Path:
    """保存文章到输出目录，以文章标题命名。"""
    output_dir = Path(settings.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    front_matter = _extract_front_matter(content, style)
    title = _extract_title_for_filename(content) or f"{style}文章"
    body = _clean_body(content)
    refs = _extract_references(content)
    if refs:
        ref_pos = body.rfind("### 参考来源")
        if ref_pos != -1:
            body = body[:ref_pos].strip()

    today = datetime.now().strftime("%Y%m%d")
    filename = f"{today}_{title}.md"
    filepath = output_dir / filename

    final = front_matter + "\n\n" + body
    if refs:
        final += "\n\n### 参考来源\n" + refs

    filepath.write_text(final, encoding="utf-8")
    logger.info(f"文章已保存: {filepath}")
    return filepath


def _extract_title_for_filename(content: str) -> str:
    """从 AI 输出中提取标题，清理后用作文件名。"""
    title = _extract_title_from_content(content)
    if not title:
        return ""
    # 如果提取到的还是元信息名，放弃
    if _is_meta_name(title):
        return ""
        return ""

    valid = re.sub(r'[\\/:*?"<>|]', "", title)
    valid = valid.strip().replace(" ", "_")
    if len(valid) > 60:
        valid = valid[:60].rstrip("_")
    return valid


def save_memo(content: str) -> Path:
    """保存备忘录。"""
    memo_dir = Path(settings.memo_dir)
    memo_dir.mkdir(parents=True, exist_ok=True)

    today = datetime.now().strftime("%Y%m%d")
    filepath = memo_dir / f"{today}_memo.md"
    filepath.write_text(content, encoding="utf-8")
    logger.info(f"备忘录已保存: {filepath}")
    return filepath
