"""
知乎科技前沿内容系统 —— 每日主流程。

流程：
1. 采集：从 RSS 源获取科技前沿信息
2. 筛选：AI 判断哪些话题值得写
3. 决策：是否成文、写哪类文章
4. 写作：生成知乎文章草稿
5. 保存：输出到本地 Markdown 文件

用法：
    python main.py                    # 运行完整流程
    python main.py --collect-only     # 只采集，不写作
    python main.py --dry-run          # 采集+筛选，不写作（测试用）
    python main.py --tabbit           # 写作后自动生成 Tabbit 发布指令包
"""

import argparse
import sys

from collector import collect_all
from config.settings import settings
from utils.logger import get_logger
from writer.article_generator import (
    save_article,
    save_memo,
    screen_articles,
    write_article,
    write_memo,
)

logger = get_logger(__name__)


def run_pipeline(dry_run: bool = False, collect_only: bool = False, tabbit: bool = False):
    """执行每日内容生产流程。"""

    # 检查 API Key
    if not settings.ai_api_key and not collect_only:
        logger.error("未配置 AI_API_KEY，无法写作。请先设置 .env 文件。")
        logger.info("参考 .env.example 配置后重试，或使用 --collect-only 只采集不写作。")
        if not dry_run:
            sys.exit(1)

    # === 1. 采集 ===
    logger.info("=" * 40)
    logger.info("开始采集科技前沿信息...")
    articles = collect_all()

    if not articles:
        logger.warning("未采集到任何文章，流程结束。")
        return

    if collect_only:
        logger.info(f"采集完成，共 {len(articles)} 篇文章。查看 output/ 目录。")
        save_memo("\n".join(f"- [{a.title}]({a.url})" for a in articles))
        return

    # === 2. 筛选 ===
    logger.info("=" * 40)
    logger.info("开始筛选素材...")
    screening_result = screen_articles(articles)
    save_memo(screening_result)

    # 简单判断：让 AI 在输出中包含关键词
    decision_lower = screening_result.lower()

    should_write_interpret = any(kw in decision_lower for kw in ["解读", "interpret", "两篇"])
    should_write_opportunity = any(kw in decision_lower for kw in ["机会拆解", "opportunity", "两篇"])
    should_skip = any(kw in decision_lower for kw in [
        "不写", "不建议", "素材不足", "质量不足", "不推荐",
    ])

    if dry_run:
        logger.info("干跑模式结束，未生成文章。")
        logger.info(f"筛选结论预览:\n{screening_result[:500]}")
        return

    # === 3. 写作 ===
    written_files = []
    if should_skip and not should_write_interpret and not should_write_opportunity:
        logger.info("素材质量不足，输出观察备忘录。")
        memo = write_memo(articles)
        save_memo(memo)
        logger.info("今日流程结束。")
        return

    if should_write_interpret:
        logger.info("开始撰写科技前沿解读文章...")
        article = write_article(articles, style="解读")
        path = save_article(article, style="解读")
        written_files.append(path)
        logger.info(f"解读文章已保存: {path}")

    if should_write_opportunity:
        logger.info("开始撰写机会拆解文章...")
        article = write_article(articles, style="机会拆解")
        path = save_article(article, style="机会拆解")
        written_files.append(path)
        logger.info(f"机会拆解已保存: {path}")

    logger.info("=" * 40)
    logger.info("今日流程完成！请检查 output/ 目录下的文章草稿。")
    logger.info("发布前请人工审核内容准确性。")

    if tabbit and written_files:
        _generate_tabbit_packages(written_files)


def _generate_tabbit_packages(filepaths: list):
    """为生成的文章生成 Tabbit 发布指令包。"""
    from publisher.tabbit_export import export
    from pathlib import Path
    output_dir = Path(settings.output_dir)

    for fp in filepaths:
        output_path = output_dir / f"{fp.stem}_发布指令.md"
        export(Path(fp), output_path)


def main():
    parser = argparse.ArgumentParser(description="知乎科技前沿内容生产系统")
    parser.add_argument("--collect-only", action="store_true", help="只采集，不写作")
    parser.add_argument("--dry-run", action="store_true", help="采集+筛选，不写作")
    parser.add_argument("--tabbit", action="store_true", help="写作后自动生成 Tabbit 发布指令包")
    args = parser.parse_args()

    run_pipeline(dry_run=args.dry_run, collect_only=args.collect_only, tabbit=args.tabbit)


if __name__ == "__main__":
    main()
