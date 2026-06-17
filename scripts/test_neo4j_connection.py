"""Test Neo4j connection script.

Tests connectivity to the Neo4j database using the configuration
from environment variables or .env file.

Usage:
    python scripts/test_neo4j_connection.py
"""

import os
import sys
from pathlib import Path

# Force UTF-8 output for emoji and Chinese characters
if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass


def test_connection():
    uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    user = os.getenv("NEO4J_USER", "neo4j")
    password = os.getenv("NEO4J_PASSWORD", "")

    print("=" * 60)
    print("Neo4j 连接测试")
    print("=" * 60)
    print(f"  目标 URI:  {uri}")
    print(f"  用户名:    {user}")
    print(f"  密码:      {'*' * len(password) if password else '(空)'}")
    print()

    if not uri:
        print("❌ NEO4J_URI 未配置，系统将使用内存图存储。")
        print("   如需启用 Neo4j，请在 .env 文件中设置 NEO4J_URI。")
        return False

    try:
        from neo4j import GraphDatabase

        driver = GraphDatabase.driver(uri, auth=(user, password))
        driver.verify_connectivity()
        print("✅ Neo4j TCP 连接验证通过！")
        print()

        with driver.session() as session:
            result = session.run("RETURN 1 AS n")
            record = result.single()
            print(f"✅ 基本查询测试通过: RETURN 1 = {record['n']}")

            result = session.run(
                "CALL dbms.components() "
                "YIELD name, versions, edition "
                "RETURN name, versions, edition"
            )
            for record in result:
                ver = ", ".join(record["versions"])
                print(
                    f"✅ Neo4j 版本信息: {record['name']} {ver} ({record['edition']})"
                )

            result = session.run("CALL db.labels() YIELD label RETURN label")
            labels = [record["label"] for record in result]
            if labels:
                print(f"✅ 已有标签: {', '.join(labels)}")
            else:
                print("ℹ️  数据库中暂无标签")

            result = session.run("MATCH (n) RETURN count(n) AS count")
            node_count = result.single()["count"]
            print(f"✅ 节点数量: {node_count}")
            print()

        driver.close()
        print("=" * 60)
        print("连接测试全部通过！Neo4j 正常运行。")
        print("=" * 60)
        return True

    except Exception as e:
        print(f"❌ Neo4j 连接失败: {e}")
        print()
        print("=" * 60)
        print("系统未检测到运行中的 Neo4j 图数据库。")
        print()
        print("如需安装 Neo4j，请选择以下方式之一：")
        print()
        print("  1. Docker (推荐):")
        print("     docker run -d \\")
        print("       --name neo4j \\")
        print("       -p 7474:7474 -p 7687:7687 \\")
        print("       -e NEO4J_AUTH=neo4j/neo4j123 \\")
        print("       neo4j:5-community")
        print()
        print("  2. Windows 安装包:")
        print("     https://neo4j.com/download-center/#community")
        print()
        print("  3. Neo4j Desktop (图形化工具):")
        print("     https://neo4j.com/download/")
        print()
        print("系统将自动降级使用内存图存储（_InMemoryGraph），")
        print("不影响应用程序的正常运行。")
        print("=" * 60)
        return False


if __name__ == "__main__":
    success = test_connection()
    sys.exit(0 if success else 1)
