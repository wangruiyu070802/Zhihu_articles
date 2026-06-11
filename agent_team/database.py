"""Agent Team 任务数据库。

SQLite 存储，支持多 agent 并发读写、状态追踪。
每个 agent 独立处理自己的任务阶段，通过数据库传递结果。

任务流水线状态：pending → in_progress → completed / failed

表结构：
- article_sets: 采集批次（一次采集任务的结果集）
- articles: 单篇文章记录
- screening_results: 筛选结果（每个 article_set 一次）
- articles_written: 已生成的文章草稿
"""

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional


DB_PATH = Path(__file__).parent.parent / "data" / "agent_team.db"


def get_db() -> sqlite3.Connection:
    """获取数据库连接。"""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    """初始化数据库表结构。"""
    with get_db() as db:
        db.executescript("""
            CREATE TABLE IF NOT EXISTS article_sets (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at  TEXT NOT NULL DEFAULT (datetime('now','localtime')),
                source_count INTEGER DEFAULT 0,
                article_count INTEGER DEFAULT 0,
                status      TEXT NOT NULL DEFAULT 'pending',
                -- pending / screening / screened / writing / written / failed
                error       TEXT
            );

            CREATE TABLE IF NOT EXISTS articles (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                set_id          INTEGER NOT NULL REFERENCES article_sets(id),
                title           TEXT NOT NULL,
                url             TEXT NOT NULL,
                summary         TEXT DEFAULT '',
                source_name     TEXT DEFAULT '',
                source_category TEXT DEFAULT '',
                published_at    TEXT,
                collected_at    TEXT DEFAULT (datetime('now','localtime'))
            );

            CREATE TABLE IF NOT EXISTS screening_results (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                set_id          INTEGER NOT NULL REFERENCES article_sets(id),
                decision        TEXT NOT NULL,
                -- interpret / opportunity / both / skip
                full_result     TEXT NOT NULL,
                created_at      TEXT DEFAULT (datetime('now','localtime')),
                UNIQUE(set_id)
            );

            CREATE TABLE IF NOT EXISTS articles_written (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                set_id          INTEGER NOT NULL REFERENCES article_sets(id),
                style           TEXT NOT NULL,
                -- interpret / opportunity
                filepath        TEXT NOT NULL,
                title           TEXT DEFAULT '',
                word_count      INTEGER DEFAULT 0,
                status          TEXT NOT NULL DEFAULT 'pending',
                -- pending / published / failed
                created_at      TEXT DEFAULT (datetime('now','localtime'))
            );

            CREATE INDEX IF NOT EXISTS idx_articles_set ON articles(set_id);
            CREATE INDEX IF NOT EXISTS idx_article_sets_status ON article_sets(status);
        """)


# ---- ArticleSet 操作 ----

def create_article_set(source_count: int, article_count: int) -> int:
    """创建新的采集批次，返回 ID。"""
    with get_db() as db:
        cur = db.execute(
            "INSERT INTO article_sets (source_count, article_count, status) VALUES (?, ?, 'pending')",
            (source_count, article_count),
        )
        return cur.lastrowid


def update_set_status(set_id: int, status: str, error: str = ""):
    with get_db() as db:
        db.execute(
            "UPDATE article_sets SET status=?, error=? WHERE id=?",
            (status, error, set_id),
        )


def get_pending_sets(status: str = "pending") -> list[dict]:
    """获取指定状态的采集批次。"""
    with get_db() as db:
        rows = db.execute(
            "SELECT * FROM article_sets WHERE status=? ORDER BY id ASC", (status,)
        ).fetchall()
        return [dict(r) for r in rows]


def get_latest_set() -> Optional[dict]:
    """获取最近一次采集批次。"""
    with get_db() as db:
        row = db.execute(
            "SELECT * FROM article_sets ORDER BY id DESC LIMIT 1"
        ).fetchone()
        return dict(row) if row else None


# ---- Article 操作 ----

def save_articles(set_id: int, articles: list) -> int:
    """批量保存文章，返回数量。"""
    with get_db() as db:
        for a in articles:
            db.execute(
                """INSERT INTO articles (set_id, title, url, summary, source_name, source_category, published_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (set_id, a.title, a.url, a.summary[:1000], a.source_name,
                 a.source_category, str(a.published) if a.published else None),
            )
        return len(articles)


def get_articles_by_set(set_id: int) -> list[dict]:
    """获取某批次的所有文章。"""
    with get_db() as db:
        rows = db.execute(
            "SELECT * FROM articles WHERE set_id=? ORDER BY id", (set_id,)
        ).fetchall()
        return [dict(r) for r in rows]


# ---- Screening 操作 ----

def save_screening(set_id: int, decision: str, full_result: str):
    """保存筛选结果。"""
    with get_db() as db:
        db.execute(
            """INSERT OR REPLACE INTO screening_results (set_id, decision, full_result)
               VALUES (?, ?, ?)""",
            (set_id, decision, full_result),
        )


def get_screening(set_id: int) -> Optional[dict]:
    """获取筛选结果。"""
    with get_db() as db:
        row = db.execute(
            "SELECT * FROM screening_results WHERE set_id=?", (set_id,)
        ).fetchone()
        return dict(row) if row else None


# ---- Written Article 操作 ----

def save_written_article(set_id: int, style: str, filepath: str, title: str, word_count: int):
    """记录已生成的文章。"""
    with get_db() as db:
        db.execute(
            """INSERT INTO articles_written (set_id, style, filepath, title, word_count)
               VALUES (?, ?, ?, ?, ?)""",
            (set_id, style, filepath, title, word_count),
        )


def get_written_articles(set_id: Optional[int] = None) -> list[dict]:
    """获取已生成的文章列表。"""
    with get_db() as db:
        if set_id:
            rows = db.execute(
                "SELECT * FROM articles_written WHERE set_id=? ORDER BY id", (set_id,)
            ).fetchall()
        else:
            rows = db.execute(
                "SELECT * FROM articles_written ORDER BY id DESC LIMIT 20"
            ).fetchall()
        return [dict(r) for r in rows]


# ---- 状态概览 ----

def get_status_summary() -> dict:
    """获取当前所有任务的状态概览。"""
    with get_db() as db:
        sets = db.execute("SELECT id, status, created_at FROM article_sets ORDER BY id DESC LIMIT 10").fetchall()
        pending_articles = db.execute("SELECT COUNT(*) FROM articles").fetchone()[0]
        written = db.execute("SELECT COUNT(*) FROM articles_written").fetchone()[0]
        return {
            "total_sets": len(sets),
            "total_articles": pending_articles,
            "total_written": written,
            "recent_sets": [
                {"id": s["id"], "status": s["status"], "created_at": s["created_at"]}
                for s in sets
            ],
        }
