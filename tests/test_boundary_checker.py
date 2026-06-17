"""适用边界提醒器模块测试.

测试场景覆盖：
1. 仅有帮信罪事实 → 应返回 NONE
2. 出现"每日验卡 + 分装袋" → 应返回 EXCEEDS_HELPER_SCOPE
3. 出现"上线安排" → 应返回 SUSPECTED_COCONSPIRATOR
"""

import pytest

from app.services.boundary_checker import BoundaryType, check_boundary


class TestBoundaryChecker:
    """边界检测器测试类."""

    def test_only_helper_crime_facts_returns_none(self):
        """测试场景1：仅有帮信罪事实 → 应返回 NONE.

        案件描述仅包含提供银行卡、帮助转账等典型帮信罪事实，
        不涉及超出职责范围或共谋嫌疑的内容。
        """
        case = {
            "case_text": """
                被告人张某提供银行卡给他人使用，帮助转账结算。
                张某出租银行卡3张，收取租金500元。
                张某不知具体上游犯罪情况。
            """
        }

        alerts = check_boundary(case)

        assert len(alerts) == 1
        assert alerts[0].boundary_type == BoundaryType.NONE
        assert "未检测到边界问题" in alerts[0].message

    def test_daily_card_verification_and_separate_bagging_returns_exceeds_scope(self):
        """测试场景2：出现"每日验卡 + 分装袋" → 应返回 EXCEEDS_HELPER_SCOPE.

        案件描述包含"每日验卡"和"分开装袋"等超出帮信罪助手职责范围的事实特征。
        """
        case = {
            "case_text": """
                被告人李某长期从事取现工作，每日验卡确保账户可用。
                将取出的现金分开装袋，按不同来源分类。
                采取防止冻结措施，分散取现时间和地点。
            """
        }

        alerts = check_boundary(case)

        # 应该检测到 EXCEEDS_HELPER_SCOPE
        exceeds_alerts = [
            a for a in alerts if a.boundary_type == BoundaryType.EXCEEDS_HELPER_SCOPE
        ]
        assert len(exceeds_alerts) > 0

        # 验证命中的关键词
        all_keywords = []
        for alert in exceeds_alerts:
            all_keywords.extend(alert.matched_keywords)

        assert "每日验卡" in all_keywords
        assert "分开装袋" in all_keywords or "分装袋" in all_keywords
        assert "防止冻结" in all_keywords

    def test_upstream_arrangement_returns_suspected_coconspirator(self):
        """测试场景3：出现"上线安排" → 应返回 SUSPECTED_COCONSPIRATOR.

        案件描述包含"上线安排"等涉嫌共谋的事实特征。
        """
        case = {
            "case_text": """
                被告人王某按照上线安排，负责在指定地点取现。
                上线每天通过微信指示取现金额和地点。
                王某按照上线要求完成取现任务。
            """
        }

        alerts = check_boundary(case)

        # 应该检测到 SUSPECTED_COCONSPIRATOR
        coconspirator_alerts = [
            a for a in alerts if a.boundary_type == BoundaryType.SUSPECTED_COCONSPIRATOR
        ]
        assert len(coconspirator_alerts) > 0

        # 验证命中的关键词
        all_keywords = []
        for alert in coconspirator_alerts:
            all_keywords.extend(alert.matched_keywords)

        assert "上线安排" in all_keywords

    def test_multiple_boundary_issues(self):
        """测试场景4：同时出现多种边界问题 → 应返回多个警告.

        案件描述同时包含超出职责范围和涉嫌共谋的事实特征。
        """
        case = {
            "case_text": """
                被告人赵某按照上线安排，长期取现分工明确。
                每日验卡确保账户正常，采取防止冻结措施。
                将现金分开装袋，抽成比例异常高。
            """
        }

        alerts = check_boundary(case)

        # 应该同时检测到 EXCEEDS_HELPER_SCOPE 和 SUSPECTED_COCONSPIRATOR
        boundary_types = {alert.boundary_type for alert in alerts}

        assert BoundaryType.EXCEEDS_HELPER_SCOPE in boundary_types
        assert BoundaryType.SUSPECTED_COCONSPIRATOR in boundary_types

    def test_empty_case_text_returns_none(self):
        """测试场景5：空案件文本 → 应返回 NONE."""
        case = {"case_text": ""}

        alerts = check_boundary(case)

        assert len(alerts) == 1
        assert alerts[0].boundary_type == BoundaryType.NONE

    def test_case_with_no_relevant_keywords_returns_none(self):
        """测试场景6：案件文本不包含相关关键词 → 应返回 NONE."""
        case = {
            "case_text": """
                被告人孙某因交通肇事被起诉。
                事故发生于2024年3月15日，造成一人受伤。
            """
        }

        alerts = check_boundary(case)

        assert len(alerts) == 1
        assert alerts[0].boundary_type == BoundaryType.NONE

    def test_case_with_partial_keywords(self):
        """测试场景7：仅包含部分关键词 → 应正确识别.

        只包含"长期取现分工"但不包含其他触发词。
        """
        case = {
            "case_text": """
                被告人周某长期取现分工，负责在A区域取现。
            """
        }

        alerts = check_boundary(case)

        # 应该检测到 EXCEEDS_HELPER_SCOPE
        exceeds_alerts = [
            a for a in alerts if a.boundary_type == BoundaryType.EXCEEDS_HELPER_SCOPE
        ]
        assert len(exceeds_alerts) > 0
        assert "长期取现分工" in exceeds_alerts[0].matched_keywords


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
