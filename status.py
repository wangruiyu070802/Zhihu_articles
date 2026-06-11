"""显示 Agent Team 运行状态。"""

from datetime import datetime
from agent_team.database import get_db, get_status_summary, init_db

init_db()

s = get_status_summary()
print(f"Total batches: {s['total_sets']}")
print(f"Total articles collected: {s['total_articles']}")
print(f"Articles written: {s['total_written']}")
print()

# Recent batches
db = get_db()
rows = db.execute(
    "SELECT id, status, created_at, article_count FROM article_sets ORDER BY id DESC LIMIT 5"
).fetchall()
print("Recent batches:")
for r in rows:
    count = r["article_count"] or "?"
    print(f"  #{r['id']} [{r['status']}] {r['created_at']} ({count} articles)")

# Recent written articles
rows = db.execute(
    "SELECT title, filepath, created_at FROM articles_written ORDER BY id DESC LIMIT 5"
).fetchall()
if rows:
    print()
    print("Latest articles:")
    for r in rows:
        print(f"  - {r['title']}")
        print(f"    {r['filepath']} ({r['created_at']})")

# Check scheduled task
print()
import subprocess
result = subprocess.run(
    ["schtasks", "/query", "/tn", "ZhihuAgentTeam", "/fo", "LIST"],
    capture_output=True, text=True, timeout=10
)
if result.returncode == 0:
    for line in result.stdout.splitlines():
        if "Status" in line or "Next Run" in line or "Schedule" in line:
            print(f"  {line.strip()}")
else:
    print("  Scheduled task: NOT INSTALLED")

# Output dir
from pathlib import Path
output_dir = Path("output")
if output_dir.exists():
    files = list(output_dir.glob("*发布指令*.md"))
    if files:
        print(f"\nReady to publish: {len(files)} articles with Tabbit instructions")
        for f in files[-3:]:
            print(f"  - {f}")
