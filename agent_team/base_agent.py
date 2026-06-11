"""Agent 基类。所有 agent 继承此类。"""

from utils.logger import get_logger


class BaseAgent:
    """Agent 基类。

    子类需要实现 run_once() 方法，返回处理的任务数。
    """

    name: str = "base"

    def __init__(self):
        self.logger = get_logger(f"agent.{self.name}")

    def run_once(self) -> int:
        """执行一轮任务，返回处理数量。"""
        raise NotImplementedError

    def run(self):
        """方便单次测试。"""
        count = self.run_once()
        self.logger.info(f"{self.name} 本轮处理 {count} 个任务")
        return count
