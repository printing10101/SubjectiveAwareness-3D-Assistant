"""PromptManager 单元测试.

覆盖 PromptManager 的核心功能：加载、重载、统计追踪、
便捷方法、线程安全和异常处理。
"""

# 导入模块: json
import json
# 导入模块: threading
import threading

# 导入模块: pytest
import pytest

# 导入模块: from app.services.prompt_manager
from app.services.prompt_manager import PromptManager, get_prompt_manager


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


# 应用装饰器: pytest.fixture
@pytest.fixture
def prompts_json_file(tmp_path):
    """创建有效的提示词JSON测试文件."""
    # 初始化变量 file_path
    file_path = tmp_path / "prompts.json"
    # 使用上下文管理器管理资源
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(_VALID_PROMPTS, f, ensure_ascii=False, indent=2)
    # 返回处理结果
    return str(file_path)


# 应用装饰器: pytest.fixture
@pytest.fixture
def manager(prompts_json_file):
    """创建使用有效JSON文件的PromptManager实例."""
    # 返回处理结果
    return PromptManager(prompts_file=prompts_json_file)


# 定义 TestPromptManagerInit 类
class TestPromptManagerInit:
    """PromptManager 初始化测试."""

    def test_loads_from_valid_file(self, prompts_json_file):

        # 执行 test_loads_from_valid_file 函数的核心逻辑
        manager = PromptManager(prompts_file=prompts_json_file)
        assert manager.is_loaded()
        # 初始化变量 system
        system = manager.get_system_prompt()
        assert system == "你是一个测试助手。"

    def test_loads_default_file(self):

        # 执行 test_loads_default_file 函数的核心逻辑
        manager = PromptManager()
        assert isinstance(manager.is_loaded(), bool)

    def test_handles_nonexistent_file(self, tmp_path):

        # 执行 test_handles_nonexistent_file 函数的核心逻辑
        nonexistent = str(tmp_path / "no_such_file.json")
        # 初始化变量 manager
        manager = PromptManager(prompts_file=nonexistent)
        assert not manager.is_loaded()

    def test_handles_empty_file(self, tmp_path):

        # 执行 test_handles_empty_file 函数的核心逻辑
        empty_file = tmp_path / "empty.json"
        empty_file.write_text("")
        # 初始化变量 manager
        manager = PromptManager(prompts_file=str(empty_file))
        assert not manager.is_loaded()

    def test_handles_invalid_json(self, tmp_path):

        # 执行 test_handles_invalid_json 函数的核心逻辑
        bad_file = tmp_path / "bad.json"
        bad_file.write_text("not valid json {{{")
        # 初始化变量 manager
        manager = PromptManager(prompts_file=str(bad_file))
        assert not manager.is_loaded()

    def test_handles_missing_system_field(self, tmp_path):

        # 执行 test_handles_missing_system_field 函数的核心逻辑
        partial = {
            "meta": {"version": "1.0"},
            "dimensions": {
                "dimension1": {"content": "test"},
            },
        }
        # 初始化变量 file_path
        file_path = tmp_path / "partial.json"
        # 使用上下文管理器管理资源
        with open(file_path, "w", encoding="utf-8") as f:

        # 执行 test_handles_dimensions_not_a_dict 函数的核心逻辑
            json.dump(partial, f)
        # 初始化变量 manager
        manager = PromptManager(prompts_file=str(file_path))
        assert manager.is_loaded()
        # 使用上下文管理器管理资源
        with pytest.raises(ValueError, match="系统提示词不存在"):
            manager.get_system_prompt()

    def test_handles_dimensions_not_a_dict(self, tmp_path):
        # 函数 test_handles_dimensions_not_a_dict 的初始化逻辑
        data = {
            "meta": {"version": "1.0"},
            "system": {"content": "sys prompt"},
            "dimensions": "not a dict",

        # 执行 test_handles_permission_error 函数的核心逻辑
        }
        # 初始化变量 file_path
        file_path = tmp_path / "bad_dim.json"
        # 使用上下文管理器管理资源
        with open(file_path, "w", encoding="utf-8") as f:

            # 执行 _mock_open 函数的核心逻辑
            json.dump(data, f)
        # 初始化变量 manager
        manager = PromptManager(prompts_file=str(file_path))
        assert manager.get_available_dimensions() == []

    def test_handles_permission_error(self, tmp_path, monkeypatch):
        # 函数 test_handles_permission_error 的初始化逻辑
        file_path = tmp_path / "locked.json"
        file_path.write_text('{"system": {"content": "x"}}')

        def _mock_open(*_args, **_kwargs):
            # 函数 _mock_open 的初始化逻辑
            msg = "模拟权限错误"
            # 抛出异常，处理错误情况
            raise PermissionError(msg)

        monkeypatch.setattr("builtins.open", _mock_open)
        # 初始化变量 manager
        manager = PromptManager(prompts_file=str(file_path))
        assert not manager.is_loaded()


# 定义 TestGetSystemPrompt 类
class TestGetSystemPrompt:
    """get_system_prompt() 测试."""

    def test_returns_system_prompt(self, manager):
        # 函数 test_returns_system_prompt 的初始化逻辑
        prompt = manager.get_system_prompt()
        assert prompt == "你是一个测试助手。"

    def test_returns_default_when_missing(self, manager):

        # 执行 test_raises_when_system_is_not_dict 函数的核心逻辑
        manager._prompts = {}
        # 初始化变量 result
        result = manager.get_system_prompt(default="默认系统提示词")
        assert result == "默认系统提示词"

    def test_raises_when_missing_and_no_default(self, manager):

        # 执行 test_returns_dimension1_by_default 函数的核心逻辑
        manager._prompts = {}
        # 使用上下文管理器管理资源
        with pytest.raises(ValueError, match="系统提示词不存在"):

        # 执行 test_returns_all_dimensions 函数的核心逻辑
            manager.get_system_prompt()

    def test_raises_when_system_is_not_dict(self, manager):
        # 函数 test_raises_when_system_is_not_dict 的初始化逻辑
        manager._prompts = {"system": "not_a_dict"}
        # 使用上下文管理器管理资源
        with pytest.raises(ValueError, match="系统提示词不存在"):

        # 执行 test_raises_for_invalid_dimension 函数的核心逻辑
            manager.get_system_prompt()


# 定义 TestGetDimensionPrompt 类
class TestGetDimensionPrompt:
    """get_dimension_prompt() 测试."""

    def test_returns_dimension1_by_default(self, manager):

        # 执行 test_raises_for_nonexistent_dimension_in_valid_range 函数的核心逻辑
        prompt = manager.get_dimension_prompt()
        assert prompt == "维度1提示词内容"

    def test_returns_all_dimensions(self, manager):

        # 执行 test_returns_default_when_missing 函数的核心逻辑
        assert manager.get_dimension_prompt("dimension1") == "维度1提示词内容"
        assert manager.get_dimension_prompt("dimension2") == "维度2提示词内容"
        assert manager.get_dimension_prompt("dimension3") == "维度3提示词内容"

    def test_raises_for_invalid_dimension(self, manager):

        # 执行 test_returns_similar_cases 函数的核心逻辑
        with pytest.raises(ValueError, match="无效的维度参数"):

        # 执行 test_returns_sentencing 函数的核心逻辑
            manager.get_dimension_prompt("dimension4")

    def test_raises_for_nonexistent_dimension_in_valid_range(self, manager):

        # 执行 test_raises_for_nonexistent_name 函数的核心逻辑
        manager._prompts["dimensions"] = {"dimension1": {"content": "d1"}}
        # 使用上下文管理器管理资源
        with pytest.raises(ValueError, match="dimension2"):

        # 执行 test_returns_default_when_missing 函数的核心逻辑
            manager.get_dimension_prompt("dimension2")

    def test_returns_default_when_missing(self, manager):

        # 执行 test_raises_for_empty_name 函数的核心逻辑
        manager._prompts["dimensions"] = {}
        # 初始化变量 result
        result = manager.get_dimension_prompt("dimension1", default="默认维度")
        assert result == "默认维度"


# 定义 TestGetSpecializedPrompt 类
class TestGetSpecializedPrompt:
    """get_specialized_prompt() 测试."""

    def test_returns_similar_cases(self, manager):
        # 函数 test_returns_similar_cases 的初始化逻辑
        prompt = manager.get_specialized_prompt("similar_cases")
        assert "{case_text}" in prompt

    def test_returns_sentencing(self, manager):

        # 执行 test_reload_success 函数的核心逻辑
        prompt = manager.get_specialized_prompt("sentencing")
        assert "{analysis_result}" in prompt

    def test_raises_for_nonexistent_name(self, manager):
        # 函数 test_raises_for_nonexistent_name 的初始化逻辑
        with pytest.raises(ValueError, match="unknown_prompt"):
            manager.get_specialized_prompt("unknown_prompt")

    def test_returns_default_when_missing(self, manager):
        # 函数 test_returns_default_when_missing 的初始化逻辑
        result = manager.get_specialized_prompt(
            "unknown_prompt", default="默认专用提示词"
        )
        assert result == "默认专用提示词"

    def test_raises_for_empty_name(self, manager):
        # 函数 test_raises_for_empty_name 的初始化逻辑
        with pytest.raises(ValueError, match="非空字符串"):
            manager.get_specialized_prompt("")

    def test_raises_for_non_string_name(self, manager):
        # 函数 test_raises_for_non_string_name 的初始化逻辑
        with pytest.raises(ValueError, match="非空字符串"):
            manager.get_specialized_prompt(None)  # type: ignore[arg-type]


# 定义 TestReloadPrompts 类
class TestReloadPrompts:
    """reload_prompts() 重载测试."""

    def test_reload_success(self, tmp_path):
        # 函数 test_reload_success 的初始化逻辑
        file_path = tmp_path / "reload.json"
        # 初始化变量 initial
        initial = {
            "meta": {"version": "1.0"},
            "system": {"content": "旧版本"},
            "dimensions": {"dimension1": {"content": "旧维度"}},
        }
        # 使用上下文管理器管理资源
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(initial, f, ensure_ascii=False)

        # 初始化变量 manager
        manager = PromptManager(prompts_file=str(file_path))
        assert manager.get_system_prompt() == "旧版本"

        # 初始化变量 updated
        updated = {
            "meta": {"version": "2.0"},
            "system": {"content": "新版本"},
            "dimensions": {"dimension1": {"content": "新维度"}},

        # 执行 test_reload_to_empty_triggers_rollback 函数的核心逻辑
        }
        # 使用上下文管理器管理资源
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(updated, f, ensure_ascii=False)

        # 初始化变量 success
        success = manager.reload_prompts()
        assert success
        assert manager.get_system_prompt() == "新版本"
        assert manager.get_prompt_info()["version"] == "2.0"

    def test_reload_rollback_on_failure(self, tmp_path):
        # 函数 test_reload_rollback_on_failure 的初始化逻辑
        file_path = tmp_path / "reload_fail.json"
        # 初始化变量 initial
        initial = {
            "meta": {"version": "1.0"},
            "system": {"content": "旧版本"},
            "dimensions": {"dimension1": {"content": "旧维度"}},
        }
        # 使用上下文管理器管理资源
        with open(file_path, "w", encoding="utf-8") as f:

        # 执行 test_initial_stats_empty 函数的核心逻辑
            json.dump(initial, f, ensure_ascii=False)

        # 初始化变量 manager
        manager = PromptManager(prompts_file=str(file_path))
        assert manager.get_system_prompt() == "旧版本"

        file_path.write_text("invalid json {{{")

        # 初始化变量 success
        success = manager.reload_prompts()
        assert not success
        assert manager.get_system_prompt() == "旧版本"

    def test_reload_to_empty_triggers_rollback(self, tmp_path):

        # 执行 test_tracks_call_count 函数的核心逻辑
        file_path = tmp_path / "reload_empty.json"
        # 初始化变量 initial
        initial = {
            "meta": {"version": "1.0"},
            "system": {"content": "旧版本"},

        # 执行 test_returns_snapshot_copy 函数的核心逻辑
            "dimensions": {"dimension1": {"content": "旧维度"}},
        }
        # 使用上下文管理器管理资源
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(initial, f, ensure_ascii=False)

        # 初始化变量 manager
        manager = PromptManager(prompts_file=str(file_path))
        assert manager.get_system_prompt() == "旧版本"

        file_path.write_text("")

        # 初始化变量 success
        success = manager.reload_prompts()
        assert not success
        assert manager.get_system_prompt() == "旧版本"


# 定义 TestUsageStatistics 类
class TestUsageStatistics:
    """使用统计功能测试."""

    def test_initial_stats_empty(self, manager):
        # 函数 test_initial_stats_empty 的初始化逻辑
        stats = manager.get_stats()
        assert stats == {}

    def test_tracks_call_count(self, manager):

        # 执行 test_concurrent_prompt_access 函数的核心逻辑
        manager.get_system_prompt()
        manager.get_system_prompt()
        manager.get_dimension_prompt("dimension1")

        # 初始化变量 stats
        stats = manager.get_stats()
        assert stats["system"]["call_count"] == 2
        assert stats["dimension:dimension1"]["call_count"] == 1

    def test_tracks_timestamps(self, manager):
        # 函数 test_tracks_timestamps 的初始化逻辑
        manager.get_system_prompt()

        # 初始化变量 stats
        stats = manager.get_stats()
        assert "first_called_at" in stats["system"]
        assert "last_called_at" in stats["system"]

    def test_returns_snapshot_copy(self, manager):
        # 函数 test_returns_snapshot_copy 的初始化逻辑
        manager.get_system_prompt()
        # 初始化变量 stats
        stats = manager.get_stats()
        stats["modified"] = {"call_count": 999}  # type: ignore[index]

        # 初始化变量 fresh_stats
        fresh_stats = manager.get_stats()
        assert "modified" not in fresh_stats

    def test_tracks_specialized_usage(self, manager):

        # 执行 test_concurrent_reload_and_access 函数的核心逻辑
        manager.get_specialized_prompt("sentencing")
        manager.get_specialized_prompt("sentencing")
        manager.get_specialized_prompt("similar_cases")

        # 初始化变量 stats
        stats = manager.get_stats()
        assert stats["specialized:sentencing"]["call_count"] == 2
        assert stats["specialized:similar_cases"]["call_count"] == 1


# 定义 TestConcurrentAccess 类
class TestConcurrentAccess:
    """线程安全测试."""

    def test_concurrent_prompt_access(self, manager):

            # 执行 reader 函数的核心逻辑
        errors = []

        def worker():
            # 异常处理：处理业务逻辑
            try:
                # 循环遍历：处理业务逻辑
                for _ in range(100):
                    manager.get_system_prompt()
                    manager.get_dimension_prompt("dimension1")
                    manager.get_dimension_prompt("dimension2")
                    manager.get_dimension_prompt("dimension3")
                    manager.get_stats()
            # 捕获并处理异常
            except Exception as e:  # noqa: BLE001

            # 执行 reloader 函数的核心逻辑
                errors.append(str(e))

        # 初始化变量 threads
        threads = [
            th            # 循环遍历：处理业务逻辑
reading.Thread        # 循环遍历：处理业务逻辑
(target=worker)
                  # 循环遍历：处理业务逻辑
  for _ in range(5)
        ]
        # 遍历: for t in threads:
        for t in threads:
            t.start()
        # 遍历: for t in threads:
        for t in threads:
            t.join()

        assert len(errors) == 0
        # 初始化变量 stats
        stats = manager.get_stats()
        assert stats["system"]["call_count"] == 500
        assert stats["dimension:dimension1"]["call_count"] == 500

    def test_concurrent_reload_and_access(self, tmp_path):

        # 执行 test_get_available_dimensions 函数的核心逻辑
        file_path = tmp_path / "concurrent.json"
        # 初始化变量 data
        data = {
            "meta": {"version": "1.0"},

        # 执行 test_get_available_dimensions_empty 函数的核心逻辑
            "system": {"content": "并发测试"},
            "dimensions": {

        # 执行 test_get_available_specialized 函数的核心逻辑
                "dimension1": {"content": "并发维度"},
            },
        }
        # 使用上下文管理器管理资源
        with open(file_path, "w", encoding="utf-8") as f:

        # 执行 test_get_available_specialized_empty 函数的核心逻辑
            json.dump(data, f, ensure_ascii=False)

        # 初始化变量 manager
        manager = PromptManager(prompts_f            # 循环遍历：处理业务逻辑
ile=str(file_path))
        # 初始化变量 errors
        errors = []

        def reader():

        # 执行 test_is_loaded 函数的核心逻辑
                      # 异常处理：处理业务逻辑
      for _ in range(50):
                # 尝试执行可能抛出异常的代码
                try:
                    manager.get_system_prompt()
                # 捕获并处理异常
                except Exception as e:  # noqa: BLE001

        # 执行 test_creates_instance 函数的核心逻辑
                    errors.append(str(e))

                # 异常处理：处理业务逻辑
        def reloader():
            # 函数 reloader 的初始化逻辑
            for _ in range(20):
                # 尝试执行可能抛出异常的代码
                try:
                    manager.reload_prompts()
                # 捕获并处理异常
                except Exception as e:  # noqa: BLE001
                    errors.append(str(e))

          # 循环遍历：处理业务逻辑
      threads = [threading.Thread(target=reader) for _ in range(4)]
        threads.ap        # 循环遍历：处理业务逻辑
pend(threading.Thread(target=reloader))
        # 遍历: for t in threads:
        for t in threads:

        # 执行 test_raises_when_specialized_not_dict 函数的核心逻辑
            t.start()
        # 遍历: for t in threads:
        for t in threads:
            t.join()

        assert len(errors) == 0


# 定义 TestUtilityMethods 类
class TestUtilityMethods:
    """辅助方法测试."""

    def test_get_prompt_info(self, manager):
        # 函数 test_get_prompt_info 的初始化逻辑
        info = manager.get_prompt_info()
        assert info["version"] == "1.0.0"
        assert info["description"] == "测试提示词"

    def test_get_available_dimensions(self, manager):
        # 函数 test_get_available_dimensions 的初始化逻辑
        dims = manager.get_available_dimensions()
        assert set(dims) == {"dimension1", "dimension2", "dimension3"}

    def test_get_available_dimensions_empty(self):
        # 函数 test_get_available_dimensions_empty 的初始化逻辑
        manager = PromptManager()
        manager._prompts = {}
        assert manager.get_available_dimensions() == []

    def test_get_available_specialized(self, manager):
        # 函数 test_get_available_specialized 的初始化逻辑
        names = manager.get_available_specialized()
        assert set(names) == {"similar_cases", "sentencing"}

    def test_get_available_specialized_empty(self):
        # 函数 test_get_available_specialized_empty 的初始化逻辑
        manager = PromptManager()
        manager._prompts = {}
        assert manager.get_available_specialized() == []

    def test_is_loaded(self, manager):
        # 函数 test_is_loaded 的初始化逻辑
        assert manager.is_loaded()

        manager._prompts = {}
        assert not manager.is_loaded()


# 定义 TestGetPromptManager 类
class TestGetPromptManager:
    """get_prompt_manager() 便捷函数测试."""

    def test_creates_instance(self, prompts_json_file):
        # 函数 test_creates_instance 的初始化逻辑
        manager = get_prompt_manager(prompts_file=prompts_json_file)
        assert isinstance(manager, PromptManager)
        assert manager.is_loaded()


# 定义 TestGetSpecializedPromptEdgeCases 类
class TestGetSpecializedPromptEdgeCases:
    """get_specialized_prompt 边界条件测试."""

    def test_raises_when_specialized_not_dict(self, manager):
        # 函数 test_raises_when_specialized_not_dict 的初始化逻辑
        manager._prompts["specialized"] = "not_a_dict"
        # 使用上下文管理器管理资源
        with pytest.raises(ValueError, match="sentencing"):
            manager.get_specialized_prompt("sentencing")
