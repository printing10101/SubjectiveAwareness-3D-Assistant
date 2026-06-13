"""检查 CASE_0000 (id=1) 的标签状态."""
from __future__ import annotations

import sqlite3
from pathlib import Path


DB_PATH = Path("C:/Users/Lenovo/Desktop/帮信罪辅助裁定软件/backend/app.db")
conn = sqlite3.connect(str(DB_PATH))
cur = conn.cursor()

cur.execute("SELECT id, title FROM cases WHERE id = 1")
print(f"Case 1: {cur.fetchone()}")

cur.execute("SELECT id, case_id, label_type, label_value, source FROM case_labels WHERE case_id = 1")
print("Labels for case 1:")
for r in cur.fetchall():
    print(f"  {r}")

cur.execute("SELECT COUNT(*) FROM case_labels WHERE label_value != '__pending__'")
print(f"\nTotal non-pending labels: {cur.fetchone()[0]}")

cur.execute("SELECT label_value, COUNT(*) FROM case_labels WHERE label_value != '__pending__' GROUP BY label_value")
print("Non-pending value distribution:")
for r in cur.fetchall():
    print(f"  {r}")

conn.close()
