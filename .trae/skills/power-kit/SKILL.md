---
name: "power-kit"
description: "全能开发工具包：集成网页抓取(Scrapling·反反爬/隐身浏览/自适应解析)、全网访问(Agent-Reach·17平台搜索/社媒/视频)、智能编排(Ruflo·Swarm多智能体/记忆学习/Hooks管道)、金融服务(IB/PE/ER·DCF/LBO建模/GL对账)和科学计算(138项技能·生物信息学/化学/药物发现/物理学/地理空间)五大模块。当需要网页抓取、爬虫、反反爬；搜索社媒内容(GitHub/小红书/抖音/推特/YouTube/Reddit等)；多智能体协作编排；金融分析建模(DCF/LBO/Comps)；或科学数据分析(基因组学/化学信息学/量子计算等)时调用此技能。"
version: "1.0.0"
metadata:
  homepage: "https://github.com/collections/power-kit"
  author: "Trae Integration"
  modules: ["scraping", "reach", "orchestration", "financial", "scientific"]
  languages: ["python", "javascript", "typescript"]
---

# Power Kit — 全能开发工具包

五大模块整合为一个 Trae 全局技能，覆盖网页抓取、全网信息获取、多智能体编排、金融分析和科学计算。

## 架构概览

```
power-kit/
├── 模块A: 网页抓取 (Scrapling)          ← Python 3.10+ 反反爬框架
├── 模块B: 全网访问 (Agent-Reach)        ← 17平台CLI/MCP搜索阅读
├── 模块C: 智能编排 (Ruflo/Claude-Flow)  ← Swarm多智能体+记忆+学习
├── 模块D: 金融服务 (Claude-FS)          ← 10+专项Agent·30+技能
└── 模块E: 科学计算 (Scientific-Agents)   ← 138项技能·100+数据库
```

## 路由表

| 用户意图 | 模块 | 详细文档 |
|---------|------|---------|
| 网页抓取/爬虫/反反爬/Cloudflare绕过/隐身浏览器/自适应解析/Spider | A | [references/scraping.md](references/scraping.md) |
| 搜索社媒/小红书/抖音/推特/微博/B站/V2EX/Reddit/LinkedIn/RSS/公众号/YouTube字幕/Exa搜索 | B | [references/reach.md](references/reach.md) |
| 多智能体协作/Swarm编排/记忆学习/Hooks管道/任务编排 | C | [references/orchestration.md](references/orchestration.md) |
| 金融分析/DCF模型/LBO模型/Comps分析/GL对账/财报审查/估值/行研/并购/Risk | D | [references/financial.md](references/financial.md) |
| 科学计算/生物信息学/化学/药物发现/基因/物理/地理空间/量子/临床研究 | E | [references/scientific.md](references/scientific.md) |

---

## 模块A：网页抓取 (Scrapling)

**能力等级：专业反反爬 + 自适应解析**

Scrapling 是一个自适应网页抓取框架，从单次请求到全量爬虫一站式支持。

### 核心能力

| 能力 | 说明 |
|------|------|
| HTTP请求 | 静态页面抓取，支持Session、Cookie、Header自定义 |
| 隐身浏览器 | Cloudflare Turnstile自动绕过，无第三方API依赖 |
| 动态浏览器 | Chromium渲染JS页面，支持网络空闲等待 |
| 自适应解析 | 网站结构变更时自动重定位元素 |
| Spider框架 | 并发爬取、暂停/恢复、自动代理轮换 |
| AI目标提取 | `--ai-targeted` 自动提取正文、过滤广告 |

### 快速命令

```bash
# 安装
pip install "scrapling[all]>=0.4.8"
scrapling install --force

# CLI抓取
scrapling extract get "https://example.com" output.md
scrapling extract fetch "https://spa-site.com" data.md --network-idle
scrapling extract stealthy-fetch "https://protected.com" content.md --solve-cloudflare

# 提取指定区域（节省Token）
scrapling extract get "https://blog.com" article.md --css-selector "article" --ai-targeted
```

### 代码示例

```python
from scrapling.fetchers import Fetcher, StealthyFetcher

# 普通请求
page = Fetcher.get('https://quotes.toscrape.com/')
quotes = page.css('.quote .text::text').getall()

# 隐身模式绕过Cloudflare
page = StealthyFetcher.fetch('https://nopecha.com/demo/cloudflare')
data = page.css('#padded_content a').getall()

# Spider爬虫
from scrapling.spiders import Spider, Response

class MySpider(Spider):
    name = "myspider"
    start_urls = ["https://example.com"]
    concurrent_requests = 10

    async def parse(self, response: Response):
        for item in response.css('.item'):
            yield {"title": item.css('h2::text').get()}
```

### 策略升级

```
静态页面 → get (最快)
     ↓ 失败/空内容
动态页面 → fetch (JS渲染)
     ↓ 被拦截
反爬页面 → stealthy-fetch (隐身绕CF)
```

详细文档 → [references/scraping.md](references/scraping.md)

---

## 模块B：全网访问 (Agent-Reach)

**能力等级：17平台统一搜索+阅读**

通过CLI/MCP/curl统一接口访问全网信息。

### 零配置即用

```bash
# Exa AI网页搜索
mcporter call 'exa.web_search_exa(query: "query", numResults: 5)'

# 通用网页阅读（Jina Reader）
curl -s "https://r.jina.ai/URL"

# GitHub搜索
gh search repos "query" --sort stars --limit 10

# Twitter搜索
twitter search "query" --limit 10

# Reddit搜索 + 读帖
rdt search "query" --limit 10
rdt read POST_ID

# YouTube/B站字幕
yt-dlp --write-sub --skip-download -o "/tmp/%(id)s" "URL"
```

### 支持平台速查

| 分类 | 平台 | 关键词触发 |
|------|------|-----------|
| **搜索** | Exa AI | 搜/查/search |
| **社媒** | 小红书/抖音/微博/Twitter/B站/V2EX/Reddit | xhs/抖音/微博/推特/b站/v2ex/reddit |
| **职场** | LinkedIn | 招聘/职位/领英 |
| **开发** | GitHub | github/代码/pr/issue |
| **网页** | 通用/RSS/公众号 | 网页/文章/rss/公众号 |
| **视频** | YouTube/B站/小宇宙 | youtube/视频/播客/字幕 |
| **金融** | 雪球(Xueqiu) | 雪球/股票/行情 |

### 环境检查

```bash
agent-reach doctor
```

详细文档 → [references/reach.md](references/reach.md)

---

## 模块C：智能编排 (Ruflo/Claude-Flow)

**能力等级：企业级多智能体协作平台**

26条CLI指令、314个MCP工具、16种智能体角色、19个AgentDB控制器、21个原生插件。

### 核心概念

```
┌──────────────────────────────────────────────────────┐
│  CLAUDE-FLOW = 编排层 (状态追踪、记忆、协调)          │
│  执行者 = 实际工作 (写代码、运行命令、创建文件)        │
└──────────────────────────────────────────────────────┘
```

### Swarm多智能体协作

```bash
# 初始化分层Swarm（8智能体）
npx claude-flow swarm init --topology hierarchical --max-agents 8
npx claude-flow agent spawn --type coder --name coder-1
npx claude-flow agent spawn --type tester --name tester-1
npx claude-flow agent spawn --type reviewer --name reviewer-1
npx claude-flow swarm start --objective "实现用户认证" --strategy development
```

### 智能体类型速查

| 类型 | 用途 |
|------|------|
| `coordinator` | 多智能体协调 |
| `coder` | 代码编写 |
| `tester` | 测试编写 |
| `reviewer` | 代码审查 |
| `architect` | 系统设计 |
| `researcher` | 需求分析 |
| `security-architect` | 安全设计 |
| `performance-engineer` | 性能优化 |

### 记忆与学习（MCP工具）

```
工作流：LEARN → COORDINATE → EXECUTE → REMEMBER

1. memory_search(query="关键词", namespace="patterns")  ← 每次任务前搜索
2. swarm_init(topology="hierarchical")                    ← 初始化协作
3. 执行实际工作                                          ← 写代码/运行命令
4. memory_store(key="pattern-x", value="成功模式")        ← 记住成功经验
```

### Hooks管道（17个Hook + 12个Worker）

后台Worker：`ultralearn`(深度学习) · `optimize`(性能优化) · `consolidate`(记忆整合) · `audit`(安全审计) · `refactor`(重构建议) · `benchmark`(性能基准) · `testgaps`(测试覆盖)

```bash
npx claude-flow hooks pre-task --description "任务描述"
npx claude-flow hooks worker dispatch --trigger audit
npx claude-flow doctor --fix
```

详细文档 → [references/orchestration.md](references/orchestration.md)

---

## 模块D：金融服务 (Claude-for-Financial-Services)

**能力等级：投行/PE/ER/资管专业级**

10+命名Agent、30+专项技能，覆盖IB、Equity Research、Private Equity、Wealth Management。

### Agent速查表

| 职能 | Agent | 能力 |
|------|-------|------|
| **投行** | Pitch Agent | Comps/Precedents/LBO → 品牌Pitch Deck |
| | Meeting Prep Agent | 客户会议前简报包 |
| **研究** | Market Researcher | 行业概况/竞争格局/对标 |
| | Earnings Reviewer | 财报电话+文件 → 模型更新 → 纪要 |
| | Model Builder | DCF/LBO/三表模型/Comps |
| **运营** | Valuation Reviewer | GP包 → 估值 → LP报告 |
| | GL Reconciler | 总账对账/差异分析/根因追踪 |
| | Month-End Closer | 应计/滚动/差异说明 |
| | Statement Auditor | LP报表审计 |
| **合规** | KYC Screener | 文件解析/规则引擎/标记缺失 |

### 核心技能

| 技能 | 用途 |
|------|------|
| `dcf-model` | DCF估值模型（含验证脚本） |
| `lbo-model` | LBO杠杆收购模型 |
| `3-statement-model` | 三表联动财务模型 |
| `comps-analysis` | 可比公司分析 |
| `competitive-analysis` | 竞争格局分析 |
| `sector-overview` | 行业概览 |
| `pitch-deck` | 投行Pitch Book |
| `earnings-analysis` | 财报分析 |
| `gl-recon` | 总账对账 |
| `nav-tieout` | NAV核对 |
| `ib-check-deck` | 投行审查清单 |

### 使用方式

```bash
# Cowork插件安装
# 设置 → 插件 → 添加 → https://github.com/anthropics/claude-for-financial-services

# Claude Code安装
claude plugin install pitch-agent@claude-for-financial-services
claude plugin install market-researcher@claude-for-financial-services
```

### 斜杠命令

`/comps` · `/dcf` · `/earnings` · `/ic-memo` · `/lbo` · `/sector` · `/pitch`

详细文档 → [references/financial.md](references/financial.md)

---

## 模块E：科学计算 (Scientific-Agent-Skills)

**能力等级：138项科学技能 + 100+数据库**

覆盖生物信息学、化学信息学、药物发现、物理学、地理空间、临床研究等。

### 领域速查

| 领域 | 代表技能 |
|------|---------|
| 🧬 生物信息学 | Scanpy, BioPython, Biopython, gget, deepTools, ETE Toolkit |
| 🧪 化学/药物发现 | RDKit, DeepChem, DiffDock, DataMol, AutoDock |
| 🔬 蛋白质组学 | ESM, FlowIO, AlphaFold |
| 🏥 临床研究 | Clinical Decision Support, Benchling, Clinical Reports |
| 🌍 地理空间 | GeoPandas, GeoMaster, BIDS |
| 🤖 ML/AI | PyTorch Lightning, Dask, scikit-learn, Cirq(量子) |
| 🔮 物理学/天文学 | AstroPy, FluidSim |
| 📊 数据分析 | EDA, Citation Management, DOCX, Geomaster |

### 100+数据库统一查询

| 数据库 | 领域 |
|--------|------|
| PubChem, ChEMBL, DrugBank, ZINC | 化学/药物 |
| UniProt, PDB, InterPro, STRING | 蛋白质 |
| COSMIC, ClinVar, gnomAD, TCGA | 癌症基因组 |
| GEO, ENCODE, SRA, ENA | 基因表达 |
| KEGG, Reactome, BioGRID | 通路/网络 |
| ClinicalTrials.gov, DailyMed, FDA | 临床 |
| FRED, BLS, Census, Treasury | 经济金融 |
| NIST, NASA, NOAA, USGS | 物理/地球 |

### 快速开始

```bash
# 克隆技能库
git clone https://github.com/K-Dense-AI/scientific-agent-skills

# 复制到项目skills目录
cp -r scientific-skills/* .trae/skills/
```

### 示例：生物信息学工作流

```python
import scanpy as sc

adata = sc.read("data.h5ad")
sc.pp.filter_cells(adata, min_genes=200)
sc.pp.normalize_total(adata, target_sum=1e4)
sc.pp.log1p(adata)
sc.tl.pca(adata, svd_solver='arpack')
sc.pp.neighbors(adata, n_neighbors=10, n_pcs=40)
sc.tl.umap(adata)
sc.tl.leiden(adata)
```

详细文档 → [references/scientific.md](references/scientific.md)

---

## 跨模块集成模式

### 模式1：研究 → 抓取 → 分析

```
[Agent-Reach 搜索] → [Scrapling 抓取详情] → [金融服务/科学计算 分析]
```

### 模式2：编排式大规模采集

```
[Orchestration Swarm] → coordinator主管
  ├── Scrapling Spider (并发采集)
  ├── Agent-Reach (补充搜索)
  └── Scientific (数据处理)
```

### 模式3：金融数据管道

```
[Agent-Reach 新闻/社媒搜索] → [Scrapling 抓取研报/财报] → [Financial Model Builder 建模]
```

---

## 错误处理与日志规范

遵循本项目编程规范，所有模块统一使用以下规范：

- **Python**: `loguru` 记录日志，捕获具体异常 → 记录 → 抛出明确错误
- **JavaScript/TypeScript**: `console.error` + try/catch，关键路径添加结构化日志
- **数据安全**: 不记录敏感信息（密码、Token、API Key）
- **降级策略**: 每个模块独立运行，单模块故障不影响其他模块

## 环境要求

| 模块 | 依赖 |
|------|------|
| 模块A Scrapling | Python 3.10+, Chromium浏览器 |
| 模块B Agent-Reach | Python 3.10+, Node.js |
| 模块C Orchestration | Node.js 20+, npm 9+ |
| 模块D Financial | Claude Cowork 或 Managed Agent API |
| 模块E Scientific | Python 3.10+，各领域专业库 |

## 快速安装

```bash
# 全局一键安装所有模块依赖
pip install "scrapling[all]>=0.4.8" agent-reach scanpy biopython rdkit deepchem astropy geopandas
npm install -g claude-flow@v3alpha

# 验证安装
scrapling --version
agent-reach doctor
npx claude-flow doctor
```
