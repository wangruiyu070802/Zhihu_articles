from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class Article(BaseModel):
    """采集到的原始文章模型。"""

    title: str
    url: str
    summary: str = ""
    content: str = ""
    author: str = ""
    published: Optional[datetime] = None
    source_name: str = ""
    source_category: str = ""
    collected_at: datetime = Field(default_factory=datetime.now)


class Collector:
    """采集器基类。"""

    def collect(self) -> list[Article]:
        raise NotImplementedError
