"""Tabbit 发布指令生成器。

将文章草稿（含 Front Matter）转换为 Tabbit 可读的完整发布指令，
涵盖知乎编辑器的所有设置项：标题、正文、封面、话题、创作声明、投稿、礼物、来源。"""

import argparse
import re
from pathlib import Path

from publisher.zhihu_agent import parse_article


def _parse_front_matter(content: str) -> dict:
    """从文章内容中解析 YAML Front Matter。"""
    fm = {}
    m = re.match(r"^---\s*\n(.+?)\n---", content, re.DOTALL)
    if not m:
        return fm

    yaml_block = m.group(1)
    current_key = None
    for line in yaml_block.split("\n"):
        # 列表项
        if line.startswith("  - "):
            val = line.strip("  - ").strip().strip('"').strip("'")
            if current_key:
                if current_key not in fm:
                    fm[current_key] = []
                fm[current_key].append(val)
            continue
        # 键值对
        if ":" in line:
            key, _, val = line.partition(":")
            current_key = key.strip()
            val = val.strip().strip('"').strip("'")
            if val and val.lower() not in ("", "null", "none"):
                fm[current_key] = val
            elif val in ("",):
                fm[current_key] = []
    return fm


def generate_instructions(filepath: Path) -> dict:
    """生成 Tabbit 指令包。"""
    content = filepath.read_text(encoding="utf-8")
    filename = filepath.stem

    # 优先从 Front Matter 读取结构化信息
    fm = _parse_front_matter(content)
    title = fm.get("title", "")
    summary = fm.get("summary", "")
    topics = fm.get("topics", [])
    cover = fm.get("cover", "")
    ai_generated = fm.get("ai_generated", "true")
    allow_gifts = fm.get("allow_gifts", "false")
    content_source = fm.get("content_source", "")
    body = ""
    article = parse_article(filepath)
    body = article["body"]

    if not title:
        title = article["title"]

    return {
        "file": filename,
        "title": title,
        "summary": summary,
        "body": body or article["body"],
        "topics": topics or ["人工智能", "科技前沿"],
        "cover": cover,
        "ai_generated": ai_generated,
        "allow_gifts": allow_gifts,
        "content_source": content_source,
        "instruction": _build_instruction(
            title=title, summary=summary, topics=topics or [],
            cover=cover, ai_generated=ai_generated,
            allow_gifts=allow_gifts, content_source=content_source,
        ),
    }


def _build_instruction(
    title: str, summary: str, topics: list[str],
    cover: str, ai_generated: str,
    allow_gifts: str, content_source: str,
) -> str:
    """生成包含完整知乎发布设置的 Tabbit 指令。"""
    lines = [
        "## Tabbit 发布指令",
        "",
        "请按以下步骤操作知乎文章编辑页，完成所有发布设置后保存草稿，不点击发布：",
        "",
        "### 步骤",
        "",
        "**1. 标题**",
        f'   填入：「{title}」',
        "",
        "**2. 正文**",
        "   将下方「正文内容」粘贴到编辑器",
        "   检查：小标题保留、段落清晰、加粗正确、列表正常",
        "",
        "**3. 封面图**",
    ]
    if cover and cover != "使用科技类相关官方配图或 AI 生成封面图":
        lines.append(f'   使用：{cover}')
    else:
        lines.append("   根据文章内容选择一张合适的封面图")
        lines.append("   优先使用文章涉及的科技公司官方产品图")
        lines.append("   或使用无明显版权的 AI 生成配图")
    lines.append("")

    # 话题
    lines.append("**4. 文章话题**")
    for t in topics[:5]:
        lines.append(f"   - 添加话题：{t}")
    lines.append("")

    # 创作声明
    lines.append("**5. 创作声明**")
    if ai_generated.lower() in ("true", "yes"):
        lines.append("   - 勾选「内容由 AI 生成」或如实声明")
        lines.append("   - 在合适位置标注：本文基于公开信息整理，部分内容由 AI 辅助生成")
    else:
        lines.append("   - 声明为原创内容")
    lines.append("")

    # 投稿至问题
    lines.extend([
        "**6. 投稿至问题（可选）**",
        "   如果文章适合回答某个知乎问题，可以投稿",
        "   不强制，跳过也可以",
        "",
        "**7. 送礼物设置**",
    ])
    if allow_gifts.lower() in ("true", "yes"):
        lines.append("   - 开启礼物功能，允许读者赠送付费礼物")
    else:
        lines.append("   - 关闭礼物功能")
    lines.append("")

    # 内容来源
    if content_source:
        lines.append(f"**8. 内容来源**")
        lines.append(f"   - 填写：{content_source}")
        lines.append("")

    # 保存
    lines.extend([
        "**9. 保存草稿**",
        "   完成以上设置后，点击「保存草稿」",
        "   不点击「发布」按钮",
        "",
    ])

    # 图片说明
    lines.append("### 图片处理")
    lines.append("- 文章中如有 ![图片]() 格式，尝试插入对应位置")
    lines.append("- 图片确定权不确定时，只留占位符「[待插入：图片说明]」")
    lines.append("- 封面图优先使用官方产品图或新闻图")
    lines.append("")

    # 边界
    lines.extend([
        "### 边界",
        "- 遇到登录、验证码、安全确认，等待用户手动操作",
        "- 不要插入来源不确定的图片",
        "- 不要修改文章核心观点",
        "- 只保存草稿，不发布",
        "- 保存后告知用户结果",
        "",
        "---",
        "## 正文内容",
        "",
    ])
    return "\n".join(lines)


def export(filepath: Path, output_path: Path):
    """导出包含完整知乎发布设置的 Tabbit 指令包。"""
    pkg = generate_instructions(filepath)

    # 话题列在顶部方便一眼看到
    topics_str = "、".join(pkg["topics"][:5]) if pkg["topics"] else "无"

    parts = [
        f"# Tabbit 发布包：{pkg['file']}",
        "",
        f"**标题：** {pkg['title']}",
        f"**话题：** {topics_str}",
        f"**AI 声明：** {'是' if pkg['ai_generated'].lower() in ('true', 'yes') else '否'}",
        f"**送礼物：** {'开启' if pkg['allow_gifts'].lower() in ('true', 'yes') else '关闭'}",
        f"**来源：** {pkg['content_source'] or '未标注'}",
        "",
        pkg["instruction"],
        pkg["body"],
    ]
    output_path.write_text("\n".join(parts), encoding="utf-8")
    print(f"[OK] 发布包已生成: {output_path}")
    print(f"  标题: {pkg['title']}")
    print(f"  话题: {topics_str}")
    print(f"  AI声明: {pkg['ai_generated']}")
    print(f"  正文: {len(pkg['body'])} 字")


def main():
    parser = argparse.ArgumentParser(description="生成 Tabbit 发布指令包")
    parser.add_argument("file", type=str, help="文章 Markdown 文件路径")
    parser.add_argument("-o", "--output", type=str, default=None, help="输出路径（默认同目录加 _发布指令 后缀）")
    args = parser.parse_args()

    filepath = Path(args.file)
    if not filepath.exists():
        print(f"文件不存在: {filepath}")
        return

    if args.output:
        output_path = Path(args.output)
    else:
        output_path = filepath.parent / f"{filepath.stem}_发布指令.md"

    export(filepath, output_path)


if __name__ == "__main__":
    main()
