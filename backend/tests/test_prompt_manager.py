"""PromptManager 单元测试.

覆盖 PromptManager 的核心功能：加载、重载、统计追踪、
便捷方法、线程安全和异常处理。
"""

import json
import threading

import pytest

from app.services.prompt import PromptManager, get_prompt_manager


_VALID_PROMPTS = {
    "meta": {
        "version": "1.0.0",
        "description": "测试提示词",
        "updated_at": "2026-05-28T00:00:00+00:00",
    },
    "system": {
        "description": "系统提示词",
        "content": "你是一个测试助手。",
    },
    "dimensions": {
        "dimension1": {
            "description": "维度1",
            "content": "维度1提示词内容",
        },
        "dimension2": {
            "description": "维度2",
            "content": "维度2提示词内容",
        },
        "dimension3": {
            "description": "维度3",
            "content": "维度3提示词内容",
        },
    },
    "specialized": {
        "similar_cases": {
            "description": "相似案例",
            "content": "推荐相似案例: {case_text}",
        },
        "sentencing": {
            "description": "量刑建议",
            "content": "量刑建议: {analysis_result}",
        },
    },
}


@pytest.fixture
def prompts_json_file(tmp_path):
    """创建有效的提示词JSON测试文件."""
    file_path = tmp_path / "prompts.json"
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(_VALID_PROMPTS, f, ensure_ascii=False, indent=2)
    return str(file_path)


@pytest.fixture
def manager(prompts_json_file):
    """创建使用有效JSON文件的PromptManager实例."""
    return PromptManager(prompts_file=prompts_json_file)


class TestPromptManagerInit:
    """PromptManager 初始化测试."""

    def test_loads_from_valid_file(self, prompts_json_file):
        manager = PromptManager(prompts_file=prompts_json_file)
        assert manager.is_loaded()
        system = manager.get_system_prompt()
        assert system == "你是一个测试助手。"

    def test_loads_default_file(self):
        manager = PromptManager()
        assert isinstance(manager.is_loaded(), bool)

    def test_handles_nonexistent_file(self, tmp_path):
        nonexistent = str(tmp_path / "no_such_file.json")
        manager = PromptManager(prompts_file=nonexistent)
        assert not manager.is_loaded()

    def test_handles_empty_file(self, tmp_path):
        empty_file = tmp_path / "empty.json"
        empty_file.write_text("")
        manager = PromptManager(prompts_file=str(empty_file))
        assert not manager.is_loaded()

    def test_handles_invalid_json(self, tmp_path):
        bad_file = tmp_path / "bad.json"
        bad_file.write_text("not valid json {{{")
        manager = PromptManager(prompts_file=str(bad_file))
        assert not manager.is_loaded()

    def test_handles_missing_system_field(self, tmp_path):
        partial = {
            "meta": {"version": "1.0"},
            "dimensions": {
                "dimension1": {"content": "test"},
            },
        }
        file_path = tmp_path / "partial.json"
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(partial, f)
        manager = PromptManager(prompts_file=str(file_path))
        assert manager.is_loaded()
        with pytest.raises(ValueError, match="系统提示词不存在"):
            manager.get_system_prompt()

    def test_handles_dimensions_not_a_dict(self, tmp_path):
        data = {
            "meta": {"version": "1.0"},
            "system": {"content": "sys prompt"},
            "dimensions": "not a dict",
        }
        file_path = tmp_path / "bad_dim.json"
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f)
        manager = PromptManager(prompts_file=str(file_path))
        assert manager.get_available_dimensions() == []

    def test_handles_permission_error(self, tmp_path, monkeypatch):
        file_path = tmp_path / "locked.json"
        file_path.write_text('{"system": {"content": "x"}}')

        def _mock_open(*_args, **_kwargs):
            msg = "模拟权限错误"
            raise PermissionError(msg)

        monkeypatch.setattr("builtins.open", _mock_open)
        manager = PromptManager(prompts_file=str(file_path))
        assert not manager.is_loaded()


class TestGetSystemPrompt:
    """get_system_prompt() 测试."""

    def test_returns_system_prompt(self, manager):
        prompt = manager.get_system_prompt()
        assert prompt == "你是一个测试助手。"

    def test_returns_default_when_missing(self, manager):
        manager._prompts = {}
        result = manager.get_system_prompt(default="默认系统提示词")
        assert result == "默认系统提示词"

    def test_raises_when_missing_and_no_default(self, manager):
        manager._prompts = {}
        with pytest.raises(ValueError, match="系统提示词不存在"):
            manager.get_system_prompt()

    def test_raises_when_system_is_not_dict(self, manager):
        manager._prompts = {"system": "not_a_dict"}
        with pytest.raises(ValueError, match="系统提示词不存在"):
            manager.get_system_prompt()


class TestGetDimensionPrompt:
    """get_dimension_prompt() 测试."""

    def test_returns_dimension1_by_default(self, manager):
        prompt = manager.get_dimension_prompt()
        assert prompt == "维度1提示词内容"

    def test_returns_all_dimensions(self, manager):
        assert manager.get_dimension_prompt("dimension1") == "维度1提示词内容"
        assert manager.get_dimension_prompt("dimension2") == "维度2提示词内容"
        assert manager.get_dimension_prompt("dimension3") == "维度3提示词内容"

    def test_raises_for_invalid_dimension(self, manager):
        with pytest.raises(ValueError, match="无效的维度参数"):
            manager.get_dimension_prompt("dimension4")

    def test_raises_for_nonexistent_dimension_in_valid_range(self, manager):
        manager._prompts["dimensions"] = {"dimension1": {"content": "d1"}}
        with pytest.raises(ValueError, match="dimension2"):
            manager.get_dimension_prompt("dimension2")

    def test_returns_default_when_missing(self, manager):
        manager._prompts["dimensions"] = {}
        result = manager.get_dimension_prompt("dimension1", default="默认维度")
        assert result == "默认维度"


class TestGetSpecializedPrompt:
    """get_specialized_prompt() 测试."""

    def test_returns_similar_cases(self, manager):
        prompt = manager.get_specialized_prompt("similar_cases")
        assert "{case_text}" in prompt

    def test_returns_sentencing(self, manager):
        prompt = manager.get_specialized_prompt("sentencing")
        assert "{analysis_result}" in prompt

    def test_raises_for_nonexistent_name(self, manager):
        with pytest.raises(ValueError, match="unknown_prompt"):
            manager.get_specialized_prompt("unknown_prompt")

    def test_returns_default_when_missing(self, manager):
        result = manager.get_specialized_prompt(
            "unknown_prompt", default="默认专用提示词"
        )
        assert result == "默认专用提示词"

    def test_raises_for_empty_name(self, manager):
        with pytest.raises(ValueError, match="非空字符串"):
            manager.get_specialized_prompt("")

    def test_raises_for_non_string_name(self, manager):
        with pytest.raises(ValueError, match="非空字符串"):
            manager.get_specialized_prompt(None)  # type: ignore[arg-type]


class TestReloadPrompts:
    """reload_prompts() 重载测试."""

    def test_reload_success(self, tmp_path):
        file_path = tmp_path / "reload.json"
        initial = {
            "meta": {"version": "1.0"},
            "system": {"content": "旧版本"},
            "dimensions": {"dimension1": {"content": "旧维度"}},
        }
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(initial, f, ensure_ascii=False)

        manager = PromptManager(prompts_file=str(file_path))
        assert manager.get_system_prompt() == "旧版本"

        updated = {
            "meta": {"version": "2.0"},
            "system": {"content": "新版本"},
            "dimensions": {"dimension1": {"content": "新维度"}},
        }
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(updated, f, ensure_ascii=False)

        success = manager.reload_prompts()
        assert success
        assert manager.get_system_prompt() == "新版本"
        assert manager.get_prompt_info()["version"] == "2.0"

    def test_reload_rollback_on_failure(self, tmp_path):
        file_path = tmp_path / "reload_fail.json"
        initial = {
            "meta": {"version": "1.0"},
            "system": {"content": "旧版本"},
            "dimensions": {"dimension1": {"content": "旧维度"}},
        }
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(initial, f, ensure_ascii=False)

        manager = PromptManager(prompts_file=str(file_path))
        assert manager.get_system_prompt() == "旧版本"

        file_path.write_text("invalid json {{{")

        success = manager.reload_prompts()
        assert not success
        assert manager.get_system_prompt() == "旧版本"

    def test_reload_to_empty_triggers_rollback(self, tmp_path):
        file_path = tmp_path / "reload_empty.json"
        initial = {
            "meta": {"version": "1.0"},
            "system": {"content": "旧版本"},
            "dimensions": {"dimension1": {"content": "旧维度"}},
        }
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(initial, f, ensure_ascii=False)

        manager = PromptManager(prompts_file=str(file_path))
        assert manager.get_system_prompt() == "旧版本"

        file_path.write_text("")

        success = manager.reload_prompts()
        assert not success
        assert manager.get_system_prompt() == "旧版本"


class TestUsageStatistics:
    """使用统计功能测试."""

    def test_initial_stats_empty(self, manager):
        stats = manager.get_stats()
        assert stats == {}

    def test_tracks_call_count(self, manager):
        manager.get_system_prompt()
        manager.get_system_prompt()
        manager.get_dimension_prompt("dimension1")

        stats = manager.get_stats()
        assert stats["system"]["call_count"] == 2
        assert stats["dimension:dimension1"]["call_count"] == 1

    def test_tracks_timestamps(self, manager):
        manager.get_system_prompt()

        stats = manager.get_stats()
        assert "first_called_at" in stats["system"]
        assert "last_called_at" in stats["system"]

    def test_returns_snapshot_copy(self, manager):
        manager.get_system_prompt()
        stats = manager.get_stats()
        stats["modified"] = {"call_count": 999}  # type: ignore[index]

        fresh_stats = manager.get_stats()
        assert "modified" not in fresh_stats

    def test_tracks_specialized_usage(self, manager):
        manager.get_specialized_prompt("sentencing")
        manager.get_specialized_prompt("sentencing")
        manager.get_specialized_prompt("similar_cases")

        stats = manager.get_stats()
        assert stats["specialized:sentencing"]["call_count"] == 2
        assert stats["specialized:similar_cases"]["call_count"] == 1


class TestConcurrentAccess:
    """线程安全测试."""

    def test_concurrent_prompt_access(self, manager):
        errors = []

        def worker():
            try:
                for _ in range(100):
                    manager.get_system_prompt()
                    manager.get_dimension_prompt("dimension1")
                    manager.get_dimension_prompt("dimension2")
                    manager.get_dimension_prompt("dimension3")
                    manager.get_stats()
            except Exception as e:  # noqa: BLE001
                errors.append(str(e))

        threads = [
            threading.Thread(target=worker)
            for _ in range(5)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        stats = manager.get_stats()
        assert stats["system"]["call_count"] == 500
        assert stats["dimension:dimension1"]["call_count"] == 500

    def test_concurrent_reload_and_access(self, tmp_path):
        file_path = tmp_path / "concurrent.json"
        data = {
            "meta": {"version": "1.0"},
            "system": {"content": "并发测试"},
            "dimensions": {
                "dimension1": {"content": "并发维度"},
            },
        }
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)

        manager = PromptManager(prompts_file=str(file_path))
        errors = []

        def reader():
            for _ in range(50):
                try:
                    manager.get_system_prompt()
                except Exception as e:  # noqa: BLE001
                    errors.append(str(e))

        def reloader():
            for _ in range(20):
                try:
                    manager.reload_prompts()
                except Exception as e:  # noqa: BLE001
                    errors.append(str(e))

        threads = [threading.Thread(target=reader) for _ in range(4)]
        threads.append(threading.Thread(target=reloader))
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0


class TestUtilityMethods:
    """辅助方法测试."""

    def test_get_prompt_info(self, manager):
        info = manager.get_prompt_info()
        assert info["version"] == "1.0.0"
        assert info["description"] == "测试提示词"

    def test_get_available_dimensions(self, manager):
        dims = manager.get_available_dimensions()
        assert set(dims) == {"dimension1", "dimension2", "dimension3"}

    def test_get_available_dimensions_empty(self):
        manager = PromptManager()
        manager._prompts = {}
        assert manager.get_available_dimensions() == []

    def test_get_available_specialized(self, manager):
        names = manager.get_available_specialized()
        assert set(names) == {"similar_cases", "sentencing"}

    def test_get_available_specialized_empty(self):
        manager = PromptManager()
        manager._prompts = {}
        assert manager.get_available_specialized() == []

    def test_is_loaded(self, manager):
        assert manager.is_loaded()

        manager._prompts = {}
        assert not manager.is_loaded()


class TestGetPromptManager:
    """get_prompt_manager() 便捷函数测试."""

    def test_creates_instance(self, prompts_json_file):
        manager = get_prompt_manager(prompts_file=prompts_json_file)
        assert isinstance(manager, PromptManager)
        assert manager.is_loaded()


class TestGetSpecializedPromptEdgeCases:
    """get_specialized_prompt 边界条件测试."""

    def test_raises_when_specialized_not_dict(self, manager):
        manager._prompts["specialized"] = "not_a_dict"
        with pytest.raises(ValueError, match="sentencing"):
            manager.get_specialized_prompt("sentencing")
