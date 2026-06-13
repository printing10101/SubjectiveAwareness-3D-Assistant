"""通过 API 填充模拟案件数据，用于测试分页接口."""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import httpx


ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


_HTTP_OK: int = 200
_HTTP_CREATED: int = 201
_EXISTING_DATA_THRESHOLD: int = 25

CASE_TITLES = [
    "张某涉嫌帮助信息网络犯罪活动案",
    "李某非法经营案",
    "王某诈骗案",
    "赵某职务侵占案",
    "陈某走私普通货物案",
    "刘某侵犯公民个人信息案",
    "杨某组织、领导传销活动案",
    "黄某开设赌场案",
    "周某非法吸收公众存款案",
    "吴某挪用资金案",
    "徐某生产、销售伪劣产品案",
    "孙某合同诈骗案",
    "马某虚开增值税专用发票案",
    "朱某非法采矿案",
    "胡某污染环境案",
    "郭某故意伤害案",
    "林某寻衅滋事案",
    "何某危险驾驶案",
    "高某侵犯著作权案",
    "罗某拒不支付劳动报酬案",
    "梁某伪造金融票证案",
    "宋某串通投标案",
    "郑某侵犯商业秘密案",
    "谢某妨害公务案",
    "唐某非法持有枪支案",
]

CASE_TEXTS = [
    "张某于2023年3月至5月期间，明知他人利用信息网络实施犯罪，仍将其名下3张银行卡提供给对方用于支付结算，涉案流水金额达人民币50余万元，张某从中获利3000元。",
    "李某未经国家有关主管部门批准，非法经营证券、期货业务，涉及金额800余万元，严重扰乱市场秩序。",
    "王某通过虚构投资项目的方式，以高额回报为诱饵，骗取多名被害人资金共计120余万元。",
    "赵某利用担任某公司财务总监的职务便利，通过虚列支出、伪造票据等方式侵占公司资金90余万元。",
    "陈某组织手下人员从境外走私普通货物入境销售，偷逃应缴税款约60万元，涉及化妆品、电子产品等。",
    "刘某通过非法手段获取公民个人信息10万余条，并将其中的部分信息出售给他人用于推销活动。",
    "杨某以发展会员返利为名，组织、领导传销活动，发展下线200余人，涉案金额500余万元。",
    "黄某在某市郊区租赁场地，设置赌博机30余台，组织多人参与赌博活动，从中抽头渔利。",
    "周某以高息为诱饵，向社会不特定对象吸收资金共计800余万元，造成投资者重大损失。",
    "吴某利用担任某公司出纳的职务便利，擅自将公司账户内的200万元资金转入其个人账户用于炒股。",
    "徐某经营一家食品加工厂，在生产过程中使用不合格原料生产伪劣产品并对外销售，销售金额达150余万元。",
    "孙某伪造公司印章及合同，以虚假项目为名与他人签订合同，骗取定金及保证金共计80余万元。",
    "马某在无真实货物交易的情况下，为他人虚开增值税专用发票，涉及税额200余万元。",
    "朱某在某县境内无证开采矿产资源，造成矿产资源破坏价值约100万元。",
    "胡某经营的化工厂违规排放废水，造成附近河流严重污染，周边居民饮用水安全受到威胁。",
    "郭某因与邻居发生口角，持刀具将对方砍伤，经鉴定为轻伤一级。",
    "林某酒后在某KTV内无故殴打他人、损毁财物，造成公共场所秩序严重混乱。",
    "何某在高速公路上醉酒驾驶，血液酒精含量达200mg/100ml，被执勤民警当场查获。",
    "高某未经著作权人许可，复制发行其计算机软件作品5000余份，非法经营数额达100余万元。",
    "罗某拖欠30余名工人工资共计60余万元长达一年，经劳动监察部门责令支付后仍拒不支付。",
    "梁某通过技术手段伪造银行存单和金融票证，用于骗取他人信任进行融资诈骗。",
    "宋某在某市政工程项目招标中，与其他投标人串通投标报价，损害招标人利益。",
    "郑某利用其在某科技公司工作的便利，窃取公司核心技术秘密提供给竞争对手，造成公司巨大经济损失。",
    "谢某在公安民警依法执行公务时，以暴力方式阻碍执法，致一名民警受伤。",
    "唐某非法持有以火药为动力发射弹丸的枪支2支，存放于其住所内，对公共安全构成严重威胁。",
] * 1

STATUSES = [
    "pending", "pending",
    "analyzing", "analyzing",
    "completed", "completed", "completed", "completed",
    "closed", "closed",
    "pending", "analyzing", "completed",
    "pending", "completed",
    "pending", "analyzing", "completed",
    "closed", "closed",
    "pending", "analyzing", "completed",
    "pending", "analyzing",
]

BASE_URL = "http://localhost:8000"


async def seed() -> None:
    """插入种子数据."""
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(f"{BASE_URL}/api/cases/?page_size=1")
        if resp.status_code == _HTTP_OK:
            data = resp.json()
            if data["total"] >= _EXISTING_DATA_THRESHOLD:
                print(f"种子数据已存在: 共 {data['total']} 条")
                return

        count = 0
        for i, (title, case_text) in enumerate(
            zip(CASE_TITLES, CASE_TEXTS, strict=True)
        ):
            status = STATUSES[i % len(STATUSES)]
            payload = {
                "title": title,
                "case_text": case_text,
                "status": status,
            }
            resp = await client.post(
                f"{BASE_URL}/api/cases/", json=payload
            )
            if resp.status_code == _HTTP_CREATED:
                count += 1
            else:
                print(
                    f"  [{resp.status_code}] 创建失败: "
                    f"{title} - {resp.text[:100]}"
                )
        print(f"成功插入 {count} 条模拟案件数据 (总计: {count})")


if __name__ == "__main__":
    asyncio.run(seed())
