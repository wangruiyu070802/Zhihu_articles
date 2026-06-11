"""RSS 采集器：从 RSS/Atom 源并行采集科技前沿信息。"""

import json
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Optional

import feedparser
import httpx

from collector.base import Article, Collector
from config.settings import settings
from utils.logger import get_logger

logger = get_logger(__name__)


class RSSSource:
    """单个 RSS 源的配置。"""

    def __init__(self, name: str, url: str, category: str, enabled: bool = True, note: str = ""):
        self.name = name
        self.url = url
        self.category = category
        self.enabled = enabled
        self.note = note

    @classmethod
    def load_all(cls) -> list["RSSSource"]:
        """从 sources.json 加载所有源配置（跳过注释行）。"""
        path = Path(__file__).parent / "sources.json"
        raw = path.read_text(encoding="utf-8")
        # 去掉注释行（"=== ... ==="）
        cleaned = re.sub(r'^\s*"[^"]*={2,}[^"]*"[^,]*,\s*$', '', raw, flags=re.MULTILINE)
        data = json.loads(cleaned)
        sources = []
        for item in data["sources"]:
            if not isinstance(item, dict):
                continue
            sources.append(cls(
                name=item["name"],
                url=item["url"],
                category=item["category"],
                enabled=item.get("enabled", True),
                note=item.get("note", ""),
            ))
        return sources

    @classmethod
    def count_enabled(cls) -> int:
        """返回启用的源数量。"""
        return sum(1 for s in cls.load_all() if s.enabled)


class RSSCollector(Collector):
    """RSS 采集器（并行）。"""

    def __init__(self, sources: Optional[list[RSSSource]] = None):
        self.sources = sources or RSSSource.load_all()

    def collect(self) -> list[Article]:
        """并行采集所有启用的 RSS/Atom 源。"""
        enabled = [s for s in self.sources if s.enabled]
        total = len(enabled)
        logger.info(f"开始并行采集 {total} 个源（并发 {settings.collect_concurrency}）...")

        all_articles: list[Article] = []
        start = time.time()

        with ThreadPoolExecutor(max_workers=settings.collect_concurrency) as pool:
            fut_map = {pool.submit(self._fetch_source, s): s for s in enabled}
            for fut in as_completed(fut_map):
                source = fut_map[fut]
                try:
                    articles = fut.result()
                    all_articles.extend(articles)
                    if articles:
                        logger.info(f"  ✓ {source.name}: {len(articles)} 篇")
                except Exception as e:
                    logger.debug(f"  ✗ {source.name}: {e}")

        # 去重（按 URL）
        seen = set()
        unique = []
        for a in sorted(all_articles, key=lambda x: x.published or datetime.min, reverse=True):
            if a.url not in seen:
                seen.add(a.url)
                unique.append(a)

        # 限制总数
        if len(unique) > settings.max_total_articles:
            unique = unique[:settings.max_total_articles]

        elapsed = time.time() - start
        logger.info(
            f"采集完成: {total} 个源 → {len(unique)} 篇文章"
            f"（去重前 {len(all_articles)}，耗时 {elapsed:.0f}s）"
        )
        return unique

    def _fetch_source(self, source: RSSSource) -> list[Article]:
        """采集单个 RSS 源。"""
        resp = httpx.get(
            source.url,
            timeout=settings.rss_timeout,
            follow_redirects=True,
            headers={"User-Agent": "Mozilla/5.0 (compatible; ZhihuArticlesBot/1.0)"},
        )
        resp.raise_for_status()

        feed = feedparser.parse(resp.text)
        articles = []
        for entry in feed.entries[:settings.max_articles_per_source]:
            published = self._parse_date(entry)
            article = Article(
                title=entry.get("title", "").strip(),
                url=entry.get("link", ""),
                summary=(entry.get("summary") or entry.get("description") or "").strip(),
                content=(
                    entry["content"][0].get("value", "")
                    if entry.get("content") else ""
                ),
                author=entry.get("author", ""),
                published=published,
                source_name=source.name,
                source_category=source.category,
            )
            articles.append(article)
        return articles

    def _parse_date(self, entry) -> Optional[datetime]:
        """尝试解析发布时间。"""
        from dateutil.parser import parse as parse_date

        for field in ("published", "updated", "created"):
            raw = entry.get(f"{field}_parsed")
            if raw:
                try:
                    from time import mktime
                    return datetime.fromtimestamp(mktime(raw))
                except Exception:
                    pass
            raw = entry.get(field)
            if raw:
                try:
                    return parse_date(raw)
                except Exception:
                    pass
        return None

    def close(self):
        pass
