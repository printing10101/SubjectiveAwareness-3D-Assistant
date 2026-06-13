# Trae Solo 提示词 - 后端代码清洗

## 任务目标
修复后端代码中的日志f-string问题，统一使用loguru的结构化日志格式。

## 执行步骤

### 步骤1: 扫描问题
```bash
cd backend
grep -r "logger\.\(info\|debug\|warning\|error\).*f\"" --include="*.py" .
grep -r "logger\.\(info\|debug\|warning\|error\).*\.format(" --include="*.py" .
```

### 步骤2: 修复日志调用
对于每个包含f-string或format的日志调用，按以下规则修复：

**修复规则**:
```python
# ❌ 修复前
logger.info(f"分析完成，耗时 {elapsed}ms")
logger.debug(f"处理案件 ID={case_id}, 文本长度={len(text)}")
logger.error("保存失败: {}".format(error))

# ✅ 修复后
logger.info("分析完成，耗时 {}ms", elapsed)
logger.debug("处理案件 ID={}, 文本长度={}", case_id, len(text))
logger.error("保存失败: {}", error)
```

**需要修复的文件**:
1. `app/routers/analysis.py` - 第62行
2. `app/services/analysis_service.py` - 第79、99行
3. 扫描发现的其他文件

### 步骤3: 验证修复
```bash
# 1. 确认没有f-string日志
grep -r "logger\.\(info\|debug\|warning\|error\).*f\"" --include="*.py" . || echo "✓ 无f-string日志"

# 2. 运行代码检查
ruff check app/ --select G004

# 3. 运行测试确保功能正常
cd backend
pytest tests/ -v --tb=short
```

### 步骤4: 提交代码
```bash
git add -A
git commit -m "style(backend): 统一日志格式，移除f-string

- 将所有logger调用从f-string改为结构化参数
- 提升日志性能和可读性
- 所有测试通过"
```

## 完成标准
- [ ] `grep` 命令返回空（无f-string日志）
- [ ] `ruff check` 无G004错误
- [ ] `pytest` 全部通过
- [ ] 代码已提交

## 注意事项
- 只修改日志调用，不修改其他f-string使用
- 保持日志消息内容不变，只改格式
- 确保参数顺序正确
