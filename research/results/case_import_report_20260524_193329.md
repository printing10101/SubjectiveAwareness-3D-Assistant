# 实验案例数据导入报告

**生成时间**: 2026-05-24 19:33:29
**数据来源**: C:\Users\Lenovo\Desktop\微信程序开发\research\cases

## 一、案例分布

| 类别 | 数量 | 占比 |
|------|------|------|
| 明知 | 15 | 60% |
| 不明知 | 5 | 20% |
| 边缘 | 5 | 20% |
| **合计** | **25** | **100%** |

目标比例: 6:2:2

## 二、数据验证结果

- 总文件数: 25
- 验证通过: 9
- 验证失败: 16

### 验证失败详情

- **GZ2023BX003.json**:
  - case_facts 长度不足 500 字 (当前 474 字)

- **GZ2023BX004.json**:
  - case_facts 长度不足 500 字 (当前 469 字)

- **GZ2023BX006.json**:
  - case_facts 长度不足 500 字 (当前 495 字)

- **GZ2023BX007.json**:
  - case_facts 长度不足 500 字 (当前 476 字)

- **GZ2023BX008.json**:
  - case_facts 长度不足 500 字 (当前 472 字)

- **GZ2023BX009.json**:
  - case_facts 长度不足 500 字 (当前 466 字)

- **GZ2023BX010.json**:
  - case_facts 长度不足 500 字 (当前 475 字)
  - 判决理由长度不足 300 字 (当前 284 字)

- **GZ2023BX011.json**:
  - case_facts 长度不足 500 字 (当前 469 字)
  - 判决理由长度不足 300 字 (当前 294 字)

- **GZ2023BX012.json**:
  - case_facts 长度不足 500 字 (当前 456 字)

- **GZ2023BX013.json**:
  - case_facts 长度不足 500 字 (当前 442 字)
  - 判决理由长度不足 300 字 (当前 269 字)

- **GZ2023BX014.json**:
  - case_facts 长度不足 500 字 (当前 459 字)
  - 判决理由长度不足 300 字 (当前 281 字)

- **GZ2023BX015.json**:
  - case_facts 长度不足 500 字 (当前 492 字)
  - 判决理由长度不足 300 字 (当前 268 字)

- **GZ2023BX017.json**:
  - case_facts 长度不足 500 字 (当前 437 字)

- **GZ2023BX018.json**:
  - case_facts 长度不足 500 字 (当前 470 字)

- **GZ2023BX019.json**:
  - case_facts 长度不足 500 字 (当前 435 字)

- **GZ2023BX020.json**:
  - case_facts 长度不足 500 字 (当前 402 字)

## 三、数据导入结果

| 指标 | 数值 |
|------|------|
| 总计 | 25 |
| 成功导入 | 0 |
| 跳过（已存在） | 0 |
| 失败 | 25 |
| 成功率 | 0.0% |

### 导入失败详情

- **GZ2023BX001.json** (GZ2023BX001): 导入过程错误: No module named 'sqlalchemy'

- **GZ2023BX002.json** (GZ2023BX002): 导入过程错误: No module named 'sqlalchemy'

- **GZ2023BX003.json** (GZ2023BX003): 导入过程错误: No module named 'sqlalchemy'

- **GZ2023BX004.json** (GZ2023BX004): 导入过程错误: No module named 'sqlalchemy'

- **GZ2023BX005.json** (GZ2023BX005): 导入过程错误: No module named 'sqlalchemy'

- **GZ2023BX006.json** (GZ2023BX006): 导入过程错误: No module named 'sqlalchemy'

- **GZ2023BX007.json** (GZ2023BX007): 导入过程错误: No module named 'sqlalchemy'

- **GZ2023BX008.json** (GZ2023BX008): 导入过程错误: No module named 'sqlalchemy'

- **GZ2023BX009.json** (GZ2023BX009): 导入过程错误: No module named 'sqlalchemy'

- **GZ2023BX010.json** (GZ2023BX010): 导入过程错误: No module named 'sqlalchemy'

- **GZ2023BX011.json** (GZ2023BX011): 导入过程错误: No module named 'sqlalchemy'

- **GZ2023BX012.json** (GZ2023BX012): 导入过程错误: No module named 'sqlalchemy'

- **GZ2023BX013.json** (GZ2023BX013): 导入过程错误: No module named 'sqlalchemy'

- **GZ2023BX014.json** (GZ2023BX014): 导入过程错误: No module named 'sqlalchemy'

- **GZ2023BX015.json** (GZ2023BX015): 导入过程错误: No module named 'sqlalchemy'

- **GZ2023BX016.json** (GZ2023BX016): 导入过程错误: No module named 'sqlalchemy'

- **GZ2023BX017.json** (GZ2023BX017): 导入过程错误: No module named 'sqlalchemy'

- **GZ2023BX018.json** (GZ2023BX018): 导入过程错误: No module named 'sqlalchemy'

- **GZ2023BX019.json** (GZ2023BX019): 导入过程错误: No module named 'sqlalchemy'

- **GZ2023BX020.json** (GZ2023BX020): 导入过程错误: No module named 'sqlalchemy'

- **GZ2023BX021.json** (GZ2023BX021): 导入过程错误: No module named 'sqlalchemy'

- **GZ2023BX022.json** (GZ2023BX022): 导入过程错误: No module named 'sqlalchemy'

- **GZ2023BX023.json** (GZ2023BX023): 导入过程错误: No module named 'sqlalchemy'

- **GZ2023BX024.json** (GZ2023BX024): 导入过程错误: No module named 'sqlalchemy'

- **GZ2023BX025.json** (GZ2023BX025): 导入过程错误: No module named 'sqlalchemy'

---

*报告由 scripts/prepare_experiment_cases.py 自动生成*