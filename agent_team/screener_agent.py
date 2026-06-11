"""筛选 Agent：对已采集的素材进行 AI 筛选和打分。"""

from agent_team.base_agent import BaseAgent
from agent_team.database import (
    get_pending_sets, update_set_status,
    get_articles_by_set, save_screening,
)
from collector.base import Article
from writer.article_generator import screen_articles


class ScreenerAgent(BaseAgent):
    """筛选 Agent。对 status=screening 的采集批次执行 AI 筛选。"""

    name = "screener"

    def run_once(self) -> int:
        pending_sets = get_pending_sets("screening")
        if not pending_sets:
            return 0

        for s in pending_sets:
            set_id = s["id"]
            self.logger.info(f"开始筛选批次 #{set_id}...")
            try:
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
                if not articles:
                    update_set_status(set_id, "failed", "无文章")
                    continue

                result = screen_articles(articles)

                decision_lower = result.lower()
                if any(kw in decision_lower for kw in ["不写", "不建议", "素材不足", "质量不足"]):
                    decision = "skip"
                elif any(kw in decision_lower for kw in ["解读", "interpret"]):
                    decision = "interpret"
                elif any(kw in decision_lower for kw in ["机会拆解", "opportunity"]):
                    decision = "opportunity"
                else:
                    has_interpret = any(kw in decision_lower for kw in ["解读", "interpret"])
                    has_opportunity = any(kw in decision_lower for kw in ["机会拆解", "opportunity"])
                    decision = "both" if (has_interpret and has_opportunity) else "interpret"

                save_screening(set_id, decision, result)

                if decision == "skip":
                    update_set_status(set_id, "skipped")
                    self.logger.info(f"批次 #{set_id} 素材不足，跳过写作")
                else:
                    update_set_status(set_id, "screened")
                    self.logger.info(f"批次 #{set_id} 筛选完成，决策: {decision}")

            except Exception as e:
                self.logger.error(f"筛选批次 #{set_id} 失败: {e}")
                update_set_status(set_id, "failed", str(e))

        return len(pending_sets)
