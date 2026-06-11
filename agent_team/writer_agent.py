"""写作 Agent：对已筛选的素材生成知乎文章。"""

import re
from pathlib import Path

from agent_team.base_agent import BaseAgent
from agent_team.database import (
    get_pending_sets, update_set_status,
    get_articles_by_set, get_screening,
    save_written_article,
)
from collector.base import Article
from config.settings import settings
from writer.article_generator import write_article, save_article


class WriterAgent(BaseAgent):
    """写作 Agent。对 status=screened 的批次执行文章生成。"""

    name = "writer"

    def run_once(self) -> int:
        pending_sets = get_pending_sets("screened")
        if not pending_sets:
            return 0

        total = 0
        for s in pending_sets:
            set_id = s["id"]
            screening = get_screening(set_id)
            if not screening:
                self.logger.warning(f"批次 #{set_id} 无筛选结果，跳过")
                update_set_status(set_id, "failed", "无筛选结果")
                continue

            decision = screening["decision"]
            articles_data = get_articles_by_set(set_id)
            articles = [
                Article(
                    title=a["title"], url=a["url"],
                    summary=a["summary"] or "",
                    source_name=a["source_name"] or "",
                    source_category=a["source_category"] or "",
                )
                for a in articles_data
            ]

            styles = []
            if decision == "both":
                styles = ["解读", "机会拆解"]
            elif decision == "interpret":
                styles = ["解读"]
            elif decision == "opportunity":
                styles = ["机会拆解"]
            else:
                update_set_status(set_id, "skipped")
                continue

            update_set_status(set_id, "writing")
            success_count = 0
            for style in styles:
                try:
                    self.logger.info(f"批次 #{set_id} 开始撰写{style}文章...")
                    content = write_article(articles, style=style)
                    path = save_article(content, style=style)

                    # 提取标题用于记录
                    title = _extract_title(content)
                    word_count = len(content)

                    save_written_article(set_id, style, str(path), title, word_count)
                    self.logger.info(f"批次 #{set_id} {style}文章已保存: {path}")
                    success_count += 1
                except Exception as e:
                    self.logger.error(f"批次 #{set_id} {style}写作失败: {e}")

            update_set_status(set_id, "written" if success_count > 0 else "failed")
            total += success_count

        return total


def _extract_title(content: str) -> str:
    """从文章内容中提取标题。"""
    m = re.search(r"## 推荐标题\s*\n(.+)", content)
    if m:
        return m.group(1).strip()
    m = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
    if m:
        return m.group(1).strip()
    return content[:80]
