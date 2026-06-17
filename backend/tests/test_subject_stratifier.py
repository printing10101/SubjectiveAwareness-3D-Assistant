"""多主体分层模块测试."""

# 导入模块: from app.services.subject_stratifier
from app.services.subject_stratifier import stratify_subjects


def test_stratify_single_subject():
    """单主体案件."""
    # 初始化变量 case_text
    case_text = "被告人张某明知他人利用信息网络实施犯罪，提供银行卡用于转账。"
    # 初始化变量 subjects
    subjects = stratify_subjects(case_text)
    assert len(subjects) == 1
    assert subjects[0].name == "张某"
    assert "提供银行卡" in subjects[0].objective_behavior


def test_stratify_multiple_subjects():
    """多主体案件."""
    # 初始化变量 case_text
    case_text = "被告人张某提供银行卡，被告人李某负责取款，被告人王某联系上线。"
    # 初始化变量 subjects
    subjects = stratify_subjects(case_text)
    assert len(subjects) == 3
    # 初始化变量 names
    names = [s.name for s in subjects]
    assert "张某" in names
    assert "李某" in names
    assert "王某" in names


def test_stratify_no_subject():
    """无明确主体."""
    # 初始化变量 case_text
    case_text = "有人提供银行卡用于犯罪。"
    # 初始化变量 subjects
    subjects = stratify_subjects(case_text)
    assert len(subjects) == 0
