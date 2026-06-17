# 模块A：Scrapling 网页抓取参考文档

## 概述

Scrapling 是自适应网页抓取框架，内核用 Rust 编写以提升性能。支持 HTTP 请求、隐身浏览器自动绕 Cloudflare、自适应解析（网站改版自动定位元素）、Spider 爬虫框架。

## 安装与初始化

```bash
pip install "scrapling[all]>=0.4.8"
scrapling install --force
```

## Fetcher 选择指南

| Fetcher | 适用场景 | 反爬能力 |
|---------|---------|---------|
| `Fetcher` / `FetcherSession` | 静态页面、博客、新闻 | 基础（TLS指纹伪装） |
| `DynamicFetcher` / `DynamicSession` | SPA应用、JS渲染页面 | 中等（真实浏览器） |
| `StealthyFetcher` / `StealthySession` | Cloudflare、反爬严格站点 | 最强（隐身浏览器+自动解CF） |

### 决策树

```
能否用 Fetcher.get() 获取？
  ├── 是 → 使用 Fetcher
  └── 否 → 页面是否依赖JS渲染？
            ├── 是 → 使用 DynamicFetcher (fetch)
            └── 否 → 是否有Cloudflare/反爬？
                      ├── 是 → 使用 StealthyFetcher (stealthy-fetch)
                      └── 否 → 检查headers/UA设置
```

## 使用模式

### 模式1：一次性请求

```python
from scrapling.fetchers import Fetcher, DynamicFetcher, StealthyFetcher

# 简单页面
page = Fetcher.get('https://example.com')

# JS渲染页面（打开浏览器→抓取→关闭）
page = DynamicFetcher.fetch('https://spa-site.com')

# 反爬绕过
page = StealthyFetcher.fetch('https://protected.com', solve_cloudflare=True)
```

### 模式2：Session复用（推荐）

保持连接、Cookie持久化、TLS指纹一致：

```python
from scrapling.fetchers import FetcherSession

with FetcherSession(impersonate='chrome') as session:
    login_page = session.get('https://site.com/login')
    # ... 登录逻辑 ...
    dashboard = session.get('https://site.com/dashboard')
```

### 模式3：隐身浏览器Session

```python
from scrapling.fetchers import StealthySession

with StealthySession(headless=True, solve_cloudflare=True) as session:
    page1 = session.fetch('https://site.com/page1')
    page2 = session.fetch('https://site.com/page2')
```

### 模式4：异步并发

```python
import asyncio
from scrapling.fetchers import AsyncStealthySession

async with AsyncStealthySession(max_pages=3) as session:
    urls = ['https://example.com/page1', 'https://example.com/page2']
    tasks = [session.fetch(url) for url in urls]
    results = await asyncio.gather(*tasks)
```

## 内容解析

### CSS选择器

```python
page.css('.class .subclass::text').get()       # 获取第一个
page.css('.class .subclass::text').getall()    # 获取全部
page.css('a::attr(href)').getall()             # 获取属性
```

### XPath

```python
page.xpath('//div[@class="item"]/span/text()').getall()
```

### BeautifulSoup风格

```python
page.find_all('div', class_='item')
page.find_by_text('关键词', tag='h2')
```

### 自适应解析

当网站结构变化时自动重定位：

```python
# 初次抓取时存储元素特征
element = page.css('.product-title')[0]

# 网站改版后自动找到对应元素
similar = element.find_similar()
```

### 元素导航

```python
element.parent          # 父元素
element.next_sibling    # 下一个兄弟
element.below_elements() # 下方所有元素
element.find_similar()  # 查找相似元素
```

## Spider爬虫框架

### 基础Spider

```python
from scrapling.spiders import Spider, Request, Response

class MySpider(Spider):
    name = "myspider"
    start_urls = ["https://quotes.toscrape.com/"]
    concurrent_requests = 10
    download_delay = 1.0
    robots_txt_obey = True

    async def parse(self, response: Response):
        for quote in response.css('.quote'):
            yield {
                "text": quote.css('.text::text').get(),
                "author": quote.css('.author::text').get(),
            }
        next_page = response.css('.next a')
        if next_page:
            yield response.follow(next_page[0].attrib['href'])

result = MySpider().start()
result.items.to_json("output.json")
```

### 多Session Spider

```python
from scrapling.spiders import Spider
from scrapling.fetchers import FetcherSession, AsyncStealthySession

class MultiSessionSpider(Spider):
    name = "multi"

    def configure_sessions(self, manager):
        manager.add("fast", FetcherSession(impersonate="chrome"))
        manager.add("stealth", AsyncStealthySession(headless=True), lazy=True)

    async def parse(self, response: Response):
        for link in response.css('a::attr(href)').getall():
            if "protected" in link:
                yield Request(link, sid="stealth")
            else:
                yield Request(link, sid="fast")
```

### CrawlSpider（规则式爬取）

```python
from scrapling.spiders import CrawlSpider, CrawlRule, LinkExtractor

class BlogCrawler(CrawlSpider):
    name = "blog"
    start_urls = ["https://example.com"]

    def rules(self):
        return [
            CrawlRule(LinkExtractor(allow=r"/posts/"), callback=self.parse_post),
            CrawlRule(LinkExtractor(allow=r"/page/\d+/")),
        ]

    async def parse_post(self, response):
        yield {"title": response.css("h1::text").get()}
```

### SitemapSpider

```python
from scrapling.spiders import SitemapSpider, CrawlRule, LinkExtractor

class MySitemap(SitemapSpider):
    name = "sitemap_spider"
    sitemap_urls = ["https://example.com/sitemap.xml"]

    def rules(self):
        return [
            CrawlRule(LinkExtractor(allow=r"/blog/"), callback=self.parse_post),
        ]

    async def parse_post(self, response):
        yield {"url": response.url, "title": response.css("h1::text").get()}
```

### 暂停/恢复

```python
# 第一次运行
spider = MySpider(crawldir="./crawl_data")
spider.start()  # Ctrl+C 暂停，自动保存进度

# 第二次运行恢复
spider = MySpider(crawldir="./crawl_data")
spider.start()  # 从断点继续
```

### 开发模式（响应缓存）

```python
class MySpider(Spider):
    development_mode = True  # 缓存响应到磁盘，调试期间不反复请求

# 发布前移除 development_mode = True
```

## CLI命令

### 安装与版本

```bash
scrapling --version
scrapling install --force
```

### 基础抓取

```bash
# GET请求 → Markdown
scrapling extract get "https://example.com" output.md

# 带CSS选择器
scrapling extract get "https://example.com" output.md -s "article"

# 带自定义Headers
scrapling extract get "https://example.com" output.md -H "User-Agent: MyBot" -H "Accept-Language: zh-CN"

# 带Cookies
scrapling extract get "https://example.com" output.md --cookies "session=abc123"

# 带超时
scrapling extract get "https://example.com" output.md --timeout 60

# 浏览器伪装
scrapling extract get "https://example.com" output.md --impersonate "chrome"

# AI目标提取（自动过滤广告/导航/页脚）
scrapling extract get "https://example.com" output.md --ai-targeted
```

### 浏览器抓取

```bash
# 动态渲染
scrapling extract fetch "https://spa-site.com" output.md --network-idle

# 等待特定元素
scrapling extract fetch "https://site.com" output.md --wait-selector ".content-loaded"

# 可见模式（调试）
scrapling extract fetch "https://site.com" output.md --no-headless

# 隐身浏览器
scrapling extract stealthy-fetch "https://protected.com" output.md

# 隐身+解Cloudflare
scrapling extract stealthy-fetch "https://cloudflare-protected.com" output.md --solve-cloudflare

# 隐身+代理
scrapling extract stealthy-fetch "https://site.com" output.md --proxy "http://proxy:8080"
```

## 安全与规范

1. **尊重 robots.txt**：Spider中设置 `robots_txt_obey = True`
2. **添加延迟**：大爬虫设置 `download_delay`
3. **只抓取授权内容**：不绕过付费墙
4. **不抓取个人/敏感数据**
5. **使用 `--ai-targeted`** 防Prompt注入
6. **清理临时文件**：抓取后删除临时输出
