#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""检查数据库状态"""

import sqlite3
import os

db_path = "app.db"

if not os.path.exists(db_path):
    print(f"数据库文件不存在: {db_path}")
    exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# 1. 检查所有表
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [row[0] for row in cursor.fetchall()]
print(f"数据库表: {tables}")

# 2. 检查用户表
if 'users' in tables:
    cursor.execute("PRAGMA table_info(users)")
    cols = cursor.fetchall()
    print(f"\nusers 表列: {[c[1] for c in cols]}")
    cursor.execute("SELECT * FROM users")
    users = cursor.fetchall()
    print(f"\n用户列表 ({len(users)} 个):")
    for user in users:
        print(f"  {user}")

# 3. 检查案件表
if 'cases' in tables:
    cursor.execute("SELECT COUNT(*) FROM cases")
    count = cursor.fetchone()[0]
    print(f"\n案件数量: {count}")

# 4. 检查知识条目表
if 'knowledge_entries' in tables:
    cursor.execute("SELECT COUNT(*) FROM knowledge_entries")
    count = cursor.fetchone()[0]
    print(f"知识条目数量: {count}")

# 5. 检查知识标签表
if 'knowledge_tags' in tables:
    cursor.execute("SELECT id, name FROM knowledge_tags LIMIT 10")
    tags = cursor.fetchall()
    print(f"\n知识标签 ({len(tags)} 个):")
    for tag in tags:
        print(f"  ID={tag[0]}, name={tag[1]}")

# 6. 检查表结构
print("\n=== 表结构检查 ===")
for table in ['users', 'cases', 'knowledge_entries', 'knowledge_tags']:
    if table in tables:
        cursor.execute(f"PRAGMA table_info({table})")
        columns = cursor.fetchall()
        print(f"\n{table} 表结构:")
        for col in columns:
            print(f"  {col[1]} ({col[2]})")

conn.close()
print("\n数据库检查完成")
