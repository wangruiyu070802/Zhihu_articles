"""Orchestrator：7x24 Agent Team 编排器。

以固定间隔循环运行所有 agent，各 agent 通过 SQLite 数据库协作。
适合 7x24 运行：直接 Python 进程，或注册为 Windows 服务。

用法：
    python -m agent_team.orchestrator              # 前台运行
    python -m agent_team.orchestrator --once       # 仅执行一轮（测试用）
    python -m agent_team.orchestrator --interval 3600  # 自定义间隔（秒）
"""

import argparse
import signal
import sys
import time
from datetime import datetime

from agent_team.collector_agent import CollectorAgent
from agent_team.database import get_status_summary, init_db
from agent_team.publisher_agent import PublisherAgent
from agent_team.screener_agent import ScreenerAgent
from agent_team.writer_agent import WriterAgent
from utils.logger import get_logger

logger = get_logger("orchestrator")

# 默认时间间隔（秒）
DEFAULT_INTERVAL = 3600  # 1 小时
DEFAULT_COLLECT_INTERVAL = 21600  # 6 小时（采集频率可以更低）


class Orchestrator:
    """Agent Team 编排器。负责调度所有 agent 按顺序执行。"""

    def __init__(self, interval: int = DEFAULT_INTERVAL, collect_interval: int = DEFAULT_COLLECT_INTERVAL):
        self.interval = interval
        self.collect_interval = collect_interval
        self.running = True
        self.last_collect_time = 0

        # 初始化数据库
        init_db()
        logger.info("Agent Team 数据库已初始化")

        # 注册 signal 处理（优雅退出）
        signal.signal(signal.SIGINT, self._handle_signal)
        signal.signal(signal.SIGTERM, self._handle_signal)

    def _handle_signal(self, signum, frame):
        logger.info("收到停止信号，正在优雅退出...")
        self.running = False

    def _should_collect(self) -> bool:
        """判断是否到了采集时间（采集频率更低）。"""
        now = time.time()
        if now - self.last_collect_time >= self.collect_interval:
            self.last_collect_time = now
            return True
        return False

    def _print_status(self):
        """打印任务状态概览。"""
        summary = get_status_summary()
        logger.info("-" * 50)
        logger.info(f"Agent Team 状态 | 总采集批次: {summary['total_sets']} "
                     f"| 文章: {summary['total_articles']} "
                     f"| 已写: {summary['total_written']}")
        for s in summary["recent_sets"][:5]:
            logger.info(f"  #{s['id']} [{s['status']}] {s['created_at']}")
        logger.info("-" * 50)

    def run_cycle(self):
        """执行一轮所有 agent。"""
        logger.info(f"===== 开始执行一轮 Agent Team ({datetime.now()}) =====")

        agents = []

        # 采集 agent：按 COLLECT_INTERVAL 执行
        if self._should_collect():
            agents.append(CollectorAgent())
        else:
            logger.info(f"未到采集时间（间隔 {self.collect_interval}s），跳过")

        # 其他 agent 每轮都检查是否有待处理任务
        agents.extend([
            ScreenerAgent(),
            WriterAgent(),
            PublisherAgent(),
        ])

        for agent in agents:
            if not self.running:
                break
            try:
                count = agent.run()
                if count > 0:
                    logger.info(f"{agent.name} 完成 {count} 个任务")
            except Exception as e:
                logger.error(f"{agent.name} 执行异常: {e}")

        self._print_status()
        logger.info(f"===== 本轮执行完毕 ({datetime.now()}) =====\n")

    def run_forever(self):
        """7x24 主循环。"""
        logger.info(f"Orchestrator 已启动 | 采集间隔={self.collect_interval}s | 调度间隔={self.interval}s")
        logger.info("按 Ctrl+C 停止")

        # 首次启动立即执行一轮
        self._should_collect()  # 重置计时器
        self.run_cycle()

        while self.running:
            try:
                time.sleep(self.interval)
                if self.running:
                    self.run_cycle()
            except KeyboardInterrupt:
                self.running = False
                break

        logger.info("Orchestrator 已停止")

    def run_once(self):
        """只执行一轮（测试用）。"""
        logger.info("单轮执行模式")
        self.run_cycle()


def main():
    parser = argparse.ArgumentParser(description="Agent Team 7x24 编排器")
    parser.add_argument("--once", action="store_true", help="只执行一轮（测试用）")
    parser.add_argument("--interval", type=int, default=DEFAULT_INTERVAL, help=f"调度间隔秒数（默认 {DEFAULT_INTERVAL}s）")
    parser.add_argument("--collect-interval", type=int, default=DEFAULT_COLLECT_INTERVAL, help=f"采集间隔秒数（默认 {DEFAULT_COLLECT_INTERVAL}s）")
    args = parser.parse_args()

    orch = Orchestrator(interval=args.interval, collect_interval=args.collect_interval)

    if args.once:
        orch.run_once()
    else:
        orch.run_forever()


if __name__ == "__main__":
    main()
