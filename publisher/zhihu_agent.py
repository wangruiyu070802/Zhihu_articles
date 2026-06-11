"""
知乎发布代理（待实现）。

目标：用 Playwright 自动化操作知乎文章编辑页，完成：
1. 登录知乎
2. 创建新文章
3. 填写标题、正文
4. 设置话题、封面
5. 保存草稿（不发布）

注意事项：
- 知乎可能有反爬/验证码，需要人工辅助首次登录
- 建议先手动登录，保存 Cookie 复用
- 敏感信息（密码）不要硬编码

用法：
    python -m publisher.zhihu_agent --article output/20250101_解读.md
"""

import argparse
import re
from pathlib import Path


def parse_article(filepath: Path) -> dict:
    """从文章 Markdown 文件中解析标题、正文、话题等信息。"""
    content = filepath.read_text(encoding="utf-8")

    title = ""
    body = content

    # 优先从 ## 推荐标题 中提取
    m = re.search(r"## 推荐标题\s*\n(.+)", content)
    if m:
        title = m.group(1).strip()
    # 其次用 ## 标题候选 中的第一个
    if not title:
        m = re.search(r"## 标题候选.*?\n\d+\.\s*(.+)", content, re.DOTALL)
        if m:
            title = m.group(1).strip()
    # 最后用文件开头的 # 标题
    if not title:
        m = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
        if m:
            title = m.group(1).strip()

    # 去掉辅助信息，只保留正文部分
    m = re.search(r"## 正文\s*\n(.+?)(?=\n## \w)", content, re.DOTALL)
    if m:
        body = m.group(1).strip()
    else:
        # 没有 ## 正文 标记时，去开头 # 标题和末尾辅助信息区后的内容
        lines = content.split("\n")
        body_start = 0
        body_end = len(lines)
        for i, line in enumerate(lines):
            if line.startswith("# ") and i == 0:
                body_start = i + 1
            if line.strip().startswith("## ") and i > 2:
                section = line.strip().lstrip("# ").strip()
                if section in ("标题候选", "话题建议", "配图建议", "来源清单", "发布前检查"):
                    body_end = i
                    break
        body = "\n".join(lines[body_start:body_end]).strip()

    return {"title": title, "body": body}


def main():
    parser = argparse.ArgumentParser(description="知乎文章发布代理")
    parser.add_argument("--article", type=str, required=True, help="文章 Markdown 文件路径")
    args = parser.parse_args()

    filepath = Path(args.article)
    if not filepath.exists():
        print(f"文件不存在: {filepath}")
        return

    article = parse_article(filepath)
    print(f"标题: {article['title']}")
    print(f"正文长度: {len(article['body'])} 字")
    print("\n[待实现] 接下来需要 Playwright 自动化操作知乎编辑器。")
    print("当前版本只做文章解析，浏览器自动化将在后续实现。")


if __name__ == "__main__":
    main()
