"""阶段 3.6 集成测试验证脚本.

验证所有合并后的服务模块是否能正常导入和使用。
"""

import sys
from pathlib import Path

# 添加 backend 到路径
backend_path = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_path))

def test_imports():
    """测试所有关键模块的导入."""
    print("=" * 60)
    print("阶段 3.6: 集成测试验证")
    print("=" * 60)

    tests = [
        # 第一批合并
        ("report.py (报告服务)", "app.services.report", ["list_reports", "generate_report", "export_pdf", "export_docx", "create_review", "get_review_statistics"]),
        ("prompt.py (提示词服务)", "app.services.prompt", ["PromptManager", "get_prompt_manager", "ANALYSIS_SYSTEM_PROMPT", "V2_DIMENSION1_PROMPT"]),
        ("version.py (版本服务)", "app.services.version", ["VersionManager", "VersionedDataLoader", "get_version_manager"]),
        ("subject.py (主体分析)", "app.services.subject", ["analyze_subjects", "stratify_subjects", "SubjectRole"]),

        # 第二批合并（已合并到新模块）
        ("analysis_helpers.py (分析辅助+档级组合)", "app.services.analysis_helpers", ["get_sentencing_suggestion", "find_similar_cases", "recognize_standard_path", "StandardPath", "combine_tiers"]),
        ("case_service.py (案件服务+系统)", "app.services.case_service", ["get_system_logs_service", "get_system_stats_service", "create_case"]),
        ("conflict_detector.py (冲突检测+证据层)", "app.services.conflict_detector", ["detect_conflicts", "analyze_evidence_layers", "check_boundary_alerts"]),

        # 核心服务
        ("pipeline (分析管道)", "app.services.pipeline", ["analyze_pipeline", "single_pass_analysis"]),
        ("analysis_service (分析服务+结论生成)", "app.services.analysis_service", ["run_analysis", "get_analysis", "get_analyses_for_case", "generate_conclusion"]),
        ("rule_engine (规则引擎)", "app.services.rule_engine", ["load_rules", "Rule"]),
        ("tag_extractor (标签抽取)", "app.services.tag_extractor", ["extract_tags", "TagMatch"]),

        # 知识库服务
        ("knowledge (知识库)", "app.services.knowledge", ["search_entries", "create_entry", "get_graph_data"]),

        # 基础服务
        ("ollama_client (LLM客户端)", "app.services.ollama_client", ["get_client", "call_ollama_with_retry"]),
        ("base_service (服务基类)", "app.services.base_service", ["BaseService"]),
    ]

    passed = 0
    failed = 0

    for name, module_name, symbols in tests:
        try:
            module = __import__(module_name, fromlist=symbols)
            missing = [s for s in symbols if not hasattr(module, s)]
            if missing:
                print(f"❌ {name}: 缺少符号 {missing}")
                failed += 1
            else:
                print(f"✅ {name}: 导入成功 ({len(symbols)} 个符号)")
                passed += 1
        except Exception as e:
            print(f"❌ {name}: 导入失败 - {e}")
            failed += 1

    print("=" * 60)
    print(f"测试结果: {passed} 通过, {failed} 失败")
    print("=" * 60)

    return failed == 0


if __name__ == "__main__":
    success = test_imports()
    sys.exit(0 if success else 1)
