"""一次性探查脚本：查看 cases/case_labels 表的当前状态."""
from __future__ import annotations

import sqlite3
from pathlib import Path


DB_PATH = Path("C:/Users/Lenovo/Desktop/帮信罪辅助裁定软件/backend/app.db")
print(f"DB: {DB_PATH}")
print(f"Exists: {DB_PATH.exists()}")

conn = sqlite3.connect(str(DB_PATH))
cur = conn.cursor()

cur.execute('SELECT name FROM sqlite_master WHERE type="table"')
tables = [r[0] for r in cur.fetchall()]
print(f"Tables: {tables}")

cur.execute("SELECT COUNT(*) FROM cases")
print(f"\nCases count: {cur.fetchone()[0]}")

cur.execute("SELECT id, title, substr(description, 1, 50) FROM cases LIMIT 5")
print("\nSample cases (id, title, description):")
for r in cur.fetchall():
    print(f"  {r}")

cur.execute("SELECT COUNT(*) FROM case_labels")
print(f"\nLabels count: {cur.fetchone()[0]}")

cur.execute("SELECT label_type, label_value, COUNT(*) FROM case_labels GROUP BY label_type, label_value ORDER BY label_type, COUNT(*) DESC")
print("\nLabels distribution:")
for r in cur.fetchall():
    print(f"  {r}")

cur.execute("SELECT label_type, COUNT(*) FROM case_labels WHERE label_value='__pending__' GROUP BY label_type")
print("\nPending labels per type:")
for r in cur.fetchall():
    print(f"  {r}")

cur.execute("SELECT COUNT(DISTINCT case_id) FROM case_labels WHERE label_value != '__pending__'")
print(f"\nCases with at least 1 real label: {cur.fetchone()[0]}")

cur.execute("""
    SELECT case_id, COUNT(*) as n 
    FROM case_labels 
    WHERE label_value != '__pending__' 
    GROUP BY case_id 
    HAVING n = 4
""")
fully_labeled = cur.fetchall()
print(f"Fully labeled cases (all 4 types): {len(fully_labeled)}")
if fully_labeled[:10]:
    print(f"  First 10: {fully_labeled[:10]}")

conn.close()
