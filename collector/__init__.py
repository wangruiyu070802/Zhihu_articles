"""采集器统一入口。"""

from collector.rss_collector import RSSCollector

__all__ = ["RSSCollector", "collect_all"]


def collect_all() -> list:
    """从所有启用的源采集文章。快捷函数。"""
    collector = RSSCollector()
    try:
        return collector.collect()
    finally:
        collector.close()
