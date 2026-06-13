# 模块D：金融服务参考文档

## 概述

Claude for Financial Services 提供投行、PE、ER、资管专业级Agent和技能。每个Agent以Cowork插件和Managed Agent两种形式交付。

**免责声明：** 所有输出均为分析师工作草稿，需经专业人员审核。不构成投资建议。

## Agent详情

### 1. Pitch Agent（投行推介）
**职能：** Coverage & Advisory

**能力流程：**
```
Comps分析 → 先例交易 → LBO模型 → 品牌Pitch Deck → 终稿
```

**使用技能：**
- `comps-analysis` · `dcf-model` · `lbo-model`
- `3-statement-model` · `sector-overview`
- `pitch-deck` · `ib-check-deck` · `deck-refresh`

### 2. Meeting Prep Agent（会议准备）
**职能：** 客户会议前简报

**能力流程：**
```
客户资料检索 → 最新新闻/财报 → 投资建议提案 → 简报包
```

**使用技能：**
- `client-review` · `client-report`
- `investment-proposal` · `pptx-author`

### 3. Market Researcher（市场研究）
**职能：** Research & Modeling

**能力流程：**
```
行业概览 → 竞争格局 → 对标 → 投资创意
```

**使用技能：**
- `sector-overview` · `competitive-analysis`
- `comps-analysis` · `idea-generation` · `pptx-author`

### 4. Earnings Reviewer（财报审查）
**职能：** 财报季自动化

**能力流程：**
```
财报电话转录 → 财报文件解析 → 模型更新 → 晨会纪要
```

**使用技能：**
- `earnings-analysis` · `earnings-preview`
- `model-update` · `morning-note`

### 5. Model Builder（模型构建）
**职能：** 金融建模

**能力流程：**
```
DCF → LBO → 三表模型 → Comps → 审查输出
```

**使用技能：**
- `dcf-model` · `lbo-model` · `3-statement-model`
- `comps-analysis` · `audit-xls` · `xlsx-author`

### 6. Valuation Reviewer（估值审查）
**职能：** PE Fund Admin

**能力流程：**
```
GP包接入 → 估值模板运行 → LP报告生成
```

**使用技能：**
- `portfolio-monitoring` · `returns-analysis`
- `ic-memo` · `xlsx-author`

### 7. GL Reconciler（总账对账）
**职能：** Finance Operations

**能力流程：**
```
发现差异 → 追踪根因 → 修复建议 → 签字流
```

**使用技能：**
- `gl-recon` · `break-trace` · `audit-xls` · `xlsx-author`

### 8. Month-End Closer（月末结账）
**职能：** 月结自动化

**能力流程：**
```
应计计算 → 滚动 → 差异说明
```

**使用技能：**
- `accrual-schedule` · `roll-forward`
- `variance-commentary` · `audit-xls` · `xlsx-author`

### 9. Statement Auditor（报表审计）
**职能：** LP报表审计

**能力流程：**
```
报表接入 → 数额核对 → 标记异常
```

**使用技能：**
- `nav-tieout` · `audit-xls` · `xlsx-author`

### 10. KYC Screener（KYC筛查）
**职能：** 合规入职

**能力流程：**
```
文件解析 → 规则引擎 → 标记缺失 → 升级
```

**使用技能：**
- `kyc-doc-parse` · `kyc-rules` · `xlsx-author`

## 核心技能详细说明

### DCF模型 (`dcf-model`)

**输入：** 历史财务报表、增长率假设、WACC
**输出：** 企业价值、股权价值、每股价值
**验证：** 内置 `validate_dcf.py` 脚本

### LBO模型 (`lbo-model`)

**输入：** 目标公司财务、债务结构、退出乘数
**输出：** IRR、MOIC、回报分析

### 三表模型 (`3-statement-model`)

**输入：** 历史BS/IS/CF
**输出：** 预测期三表联动、驱动因素分析

### Comps分析 (`comps-analysis`)

**输入：** 对标公司列表
**输出：** EV/EBITDA、P/E、P/B 等乘数对比

### 竞争分析 (`competitive-analysis`)

**输入：** 行业/赛道
**输出：** 竞争格局图、市场份额、SWOT分析

### 行业概览 (`sector-overview`)

**输入：** 行业名称
**输出：** 市场规模、增长率、趋势、监管环境

### Pitch Deck (`pitch-deck`)

**输入：** 公司资料、财务数据
**输出：** 品牌PPT、执行摘要、详细分析页

### IB检查清单 (`ib-check-deck`)

**输入：** Pitch Book草稿
**输出：** 数据交叉验证、格式检查、IB术语准确性

### 财报分析 (`earnings-analysis`)

**输入：** 财报文件（PDF/HTML）、电话会议转录
**输出：** 关键指标提取、vs一致预期对比、管理层基调分析

### GL对账 (`gl-recon`)

**输入：** 两份GL数据
**输出：** 差异清单、根因分析、修复建议

### NAV核对 (`nav-tieout`)

**输入：** LP报表、GP估值
**输出：** NAV一致性检查、异常标记

## 使用方式

```bash
# Cowork安装
# 设置 → 插件 → 添加 → https://github.com/anthropics/claude-for-financial-services

# Claude Code安装
claude plugin marketplace add anthropics/claude-for-financial-services
claude plugin install pitch-agent@claude-for-financial-services
claude plugin install model-builder@claude-for-financial-services
claude plugin install gl-reconciler@claude-for-financial-services
```

## 合作伙伴插件

### LSEG (路透社)
- 债券期货基差分析、债券相对价值、外汇套息交易
- 期权波动率分析、互换曲线策略、宏观利率监控
- 权益研究、固定收益组合审查

### S&P Global
- Tear Sheet（企业摘要/可比/行业概览）
- Earnings Preview（财报前瞻）
- Funding Digest（融资动态）

## Managed Agent部署

```bash
export ANTHROPIC_API_KEY=sk-ant-...
scripts/deploy-managed-agent.sh gl-reconciler
```

## 斜杠命令

`/comps` · `/dcf` · `/earnings` · `/ic-memo` · `/lbo` · `/sector` · `/pitch` · `/gl-recon` · `/nav-tieout` · `/kyc` · `/accrual`

## 安全合规

- 所有输出需人工审核
- 不执行交易、不入账、不批准入职
- 不构成投资建议
- 不绑定风险
