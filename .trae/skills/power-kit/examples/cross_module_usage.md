# Power Kit 使用示例

## 示例1：研究型数据采集管道

跨模块组合：Agent-Reach 搜索 → Scrapling 抓取 → 数据分析

```python
"""
场景：研究某个技术主题，搜索相关文章，抓取全文，提取关键信息
涉及模块：B(Reach) + A(Scrapling)
"""
from agent_reach import AgentReach
from scrapling.fetchers import Fetcher

reach = AgentReach()
search_results = reach.search("Python async programming best practices")

articles = []
for result in search_results[:5]:
    try:
        page = Fetcher.get(result.url, stealthy_headers=True)
        title = page.css('h1::text').get()
        content = page.css('article p::text').getall()
        articles.append({"title": title, "url": result.url, "content": "\n".join(content)})
    except Exception as e:
        print(f"抓取失败 {result.url}: {e}")

print(f"成功采集 {len(articles)} 篇文章")
```

## 示例2：新闻社交媒体监控

跨模块组合：Twitter/Reddit 搜索 → Scrapling 隐身抓取 → 数据汇总

```python
"""
场景：监控某话题的社媒讨论并抓取相关链接
涉及模块：B(Reach·社媒) + A(Scrapling·隐身)
"""
import subprocess
import json
from scrapling.fetchers import StealthyFetcher

# Twitter搜索
result = subprocess.run(
    ["twitter", "search", "AI safety", "--limit", "10", "--json"],
    capture_output=True, text=True
)
tweets = json.loads(result.stdout)

# Reddit搜索
result = subprocess.run(
    ["rdt", "search", "AI safety", "--limit", "10", "--json"],
    capture_output=True, text=True
)
posts = json.loads(result.stdout)

# 抓取分享的链接内容
for tweet in tweets:
    for url in tweet.get("urls", []):
        try:
            page = StealthyFetcher.fetch(url)
            tweet["page_content"] = page.css('article ::text').getall()
        except Exception:
            tweet["page_content"] = None

print(f"采集了 {len(tweets)} 条推文和 {len(posts)} 条Reddit帖子")
```

## 示例3：GitHub代码库批量分析

```bash
# 搜索Python AI项目
gh search repos "AI agent python" --sort stars --limit 20 --json name,url,stargazersCount

# 使用Jina Reader读取README
curl -s "https://r.jina.ai/https://github.com/owner/repo" | head -n 100
```

## 示例4：大规模网站爬取（Spider+编排）

跨模块组合：C(Orchestration) + A(Scrapling Spider)

```python
"""
场景：编排式大规模数据采集
涉及模块：C(Orchestration Swarm) + A(Scrapling Spider)
"""
from scrapling.spiders import Spider, Request, Response
from scrapling.fetchers import FetcherSession, AsyncStealthySession

class OrchestratedSpider(Spider):
    name = "orchestrated_crawl"
    start_urls = ["https://target-site.com"]
    concurrent_requests = 16
    download_delay = 0.5
    robots_txt_obey = True

    def configure_sessions(self, manager):
        manager.add("fast", FetcherSession(impersonate="chrome"))
        manager.add("stealth", AsyncStealthySession(headless=True), lazy=True)

    async def parse(self, response: Response):
        for item in response.css('.product-card'):
            detail_url = item.css('a::attr(href)').get()
            if "protected" in detail_url:
                yield Request(detail_url, sid="stealth", callback=self.parse_detail)
            else:
                yield Request(detail_url, sid="fast", callback=self.parse_detail)

    async def parse_detail(self, response: Response):
        yield {
            "title": response.css('h1::text').get(),
            "price": response.css('.price::text').get(),
            "description": response.css('.description::text').get(),
            "specs": response.css('.specs li::text').getall(),
        }

result = OrchestratedSpider(crawldir="./crawl_orch").start()
result.items.to_json("products.json")
print(f"采集了 {len(result.items)} 条产品数据")
```

## 示例5：金融研究自动化

跨模块组合：B(Web搜索) + A(抓取研报) + D(Financial模型)

```python
"""
场景：行业研究 → 数据采集 → 财务建模
涉及模块：B(Reach) + A(Scrapling) + D(Financial)
"""
# 步骤1：搜索行业新闻
# curl -s "https://r.jina.ai/https://finance.yahoo.com/industry/tech"

# 步骤2：抓取公司财报数据
from scrapling.fetchers import Fetcher

# 抓取SEC EDGAR数据
page = Fetcher.get(
    "https://www.sec.gov/cgi-bin/browse-edgar",
    params={"company": "Apple Inc", "type": "10-K"}
)
filings = page.css('.tableFile2 td a::text').getall()

# 步骤3：DCF估值
# 使用 Model Builder Agent 或 dcf-model 技能
# 输入：历史财务 + 增长率假设 → 输出：企业价值/股权价值

# 步骤4：生成Pitch Deck
# 使用 Pitch Agent
# Comps分析 → Precedents → LBO → 品牌PPT
```

## 示例6：科学数据分析工作流

跨模块组合：A(抓取论文) + E(科学计算)

```python
"""
场景：文献采集 → 生物信息学分析
涉及模块：A(Scrapling·抓摘要) + E(Scientific·Scanpy分析)
"""
import scanpy as sc
from scrapling.fetchers import Fetcher

# 步骤1：从PubMed抓取相关论文摘要
page = Fetcher.get(
    "https://pubmed.ncbi.nlm.nih.gov/",
    params={"term": "single cell RNA-seq pancreatic cancer"}
)
abstracts = page.css('.abstract-content ::text').getall()

# 步骤2：SC分析
adata = sc.read("pancreatic_cancer.h5ad")
sc.pp.filter_cells(adata, min_genes=200)
sc.pp.filter_genes(adata, min_cells=3)
sc.pp.normalize_total(adata, target_sum=1e4)
sc.pp.log1p(adata)
sc.pp.highly_variable_genes(adata, n_top_genes=2000)
sc.tl.pca(adata, svd_solver='arpack')
sc.pp.neighbors(adata, n_neighbors=10, n_pcs=40)
sc.tl.umap(adata)
sc.tl.leiden(adata, resolution=0.5)

marker_genes = sc.tl.rank_genes_groups(adata, 'leiden', method='wilcoxon')
print(f"发现 {len(adata.obs['leiden'].unique())} 个细胞亚群")
print(f"相关文献: {len(abstracts)} 篇")
```

## 示例7：CLI快速抓取模板

```bash
# 基础网页→Markdown
scrapling extract get "https://blog.example.com/article" /tmp/article.md

# 带AI内容提取（自动去广告）
scrapling extract get "https://news-site.com" /tmp/news.md --ai-targeted

# 隐身抓取Cloudflare保护页面
scrapling extract stealthy-fetch "https://protected-data.com" /tmp/data.txt --solve-cloudflare

# 读取内容并清理
cat /tmp/article.md
rm /tmp/article.md
```
