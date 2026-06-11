"""采集 Agent：从 RSS 采集科技前沿信息，存入任务数据库。"""

from agent_team.base_agent import BaseAgent
from agent_team.database import create_article_set, save_articles, update_set_status, get_pending_sets
from collector import collect_all


class CollectorAgent(BaseAgent):
    """采集 Agent。每次 run_once 执行一轮采集。"""

    name = "collector"

    def run_once(self) -> int:
        # 检查是否已有 pending 的采集批次（避免重复采集）
        pending = get_pending_sets("pending")
        if pending:
            self.logger.info(f"已有 {len(pending)} 个待处理的采集批次，跳过本轮")
            return 0

        self.logger.info("开始采集科技前沿信息...")
        try:
            articles = collect_all()
            if not articles:
                self.logger.info("本轮未采集到文章")
                return 0

            set_id = create_article_set(
                source_count=len({a.source_name for a in articles}),
                article_count=len(articles),
            )
            save_articles(set_id, articles)
            update_set_status(set_id, "screening")
            self.logger.info(f"采集完成: 批次 #{set_id}, {len(articles)} 篇文章")
            return len(articles)
        except Exception as e:
            self.logger.error(f"采集失败: {e}")
            return 0
