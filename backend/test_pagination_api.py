"""验证分页接口 JSON 返回结构."""
from __future__ import annotations

import sys
from pathlib import Path

import httpx


ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


BASE = "http://localhost:8000/api/cases/"


def show(label: str, resp: httpx.Response) -> None:
    """格式化输出单个 API 响应."""
    print("\n" + "=" * 70)
    print(f"  {label}")
    print(f"  GET {resp.url}")
    print(f"  Status: {resp.status_code}")
    data = resp.json()
    print("  Response:")
    for k, v in data.items():
        if k == "items":
            print(f"    items: [{len(v)} 条]")
            for item in v:
                print(
                    f"      - id={item['id']}, "
                    f"title={item['title'][:15]}..., "
                    f"status={item['status']}"
                )
        else:
            print(f"    {k}: {v}")
    print("=" * 70)


def run() -> None:
    """运行分页测试."""
    with httpx.Client(timeout=10, follow_redirects=True) as c:
        show(
            "场景1: 默认分页（page=1, page_size=20, "
            "sort_by=created_at desc）",
            c.get(BASE),
        )

        show(
            "场景2: 每页5条，第2页",
            c.get(BASE, params={"page": 2, "page_size": 5}),
        )

        show(
            "场景3: 按title升序排列",
            c.get(
                BASE,
                params={
                    "page": 1, "page_size": 5,
                    "sort_by": "title", "sort_order": "asc",
                },
            ),
        )

        show(
            "场景4: 筛选status=completed",
            c.get(
                BASE,
                params={
                    "page": 1, "page_size": 5,
                    "status": "completed",
                },
            ),
        )

        show(
            "场景5: 最后一页（page_size=10，查询总页数后跳到末页）",
            c.get(BASE, params={"page": 4, "page_size": 10}),
        )

        show(
            "场景6: 最小page_size=1",
            c.get(BASE, params={"page": 1, "page_size": 1}),
        )

        show(
            "场景7: page=0 无效页码 → 422",
            c.get(BASE, params={"page": 0}),
        )

        show(
            "场景8: page_size=101 超限 → 422",
            c.get(BASE, params={"page_size": 101}),
        )

        show(
            "场景9: sort_by=invalid 无效字段 → 422",
            c.get(BASE, params={"sort_by": "nonexistent"}),
        )

        show(
            "场景10: sort_order=random 无效方向 → 422",
            c.get(BASE, params={"sort_order": "random"}),
        )

        r = c.get(BASE)
        d = r.json()
        print("\n" + "=" * 70)
        print("  汇总统计")
        print(f"  数据库中案件总数: {d['total']}")
        print(f"  默认第1页返回:    {len(d['items'])} 条")
        print(f"  总页数:           {d['total_pages']}")
        print(f"  有下一页:         {d['has_next']}")
        print(f"  有上一页:         {d['has_prev']}")
        print("=" * 70)


if __name__ == "__main__":
    run()
