# 模块B：Agent-Reach 全网访问参考文档

## 概述

Agent-Reach 是17平台统一搜索+阅读工具，通过CLI/MCP/curl/Python为AI Agent提供全网信息访问能力。定位为安装器+诊断+配置层，安装后Agent直接调用上游工具。

## 架构

```
Agent-Reach CLI
  ├── channels/      # 每个平台一个文件
  │   ├── search: exa_search
  │   ├── social: bilibili, douyin, reddit, twitter, v2ex, weibo, xiaohongshu
  │   ├── career: linkedin
  │   ├── dev: github
  │   ├── web: rss, wechat, web
  │   ├── video: youtube, xiaoyuzhou
  │   └── finance: xueqiu
  ├── integrations/  # MCP Server
  └── skill/         # OpenClaw Skill
```

## 平台能力矩阵

| 平台 | 搜索 | 阅读 | 认证方式 |
|------|:----:|:----:|---------|
| Exa Search | ✅ | - | API Key |
| GitHub | ✅ | ✅ | `gh` CLI |
| Twitter/X | ✅ | ✅ | Cookie |
| Reddit | ✅ | ✅ | OAuth / `rdt` |
| 小红书 | ✅ | ✅ | Cookie |
| 抖音 | ✅ | ✅ | Cookie |
| 微博 | ✅ | ✅ | Cookie |
| B站 | ✅ | ✅ | 公开 |
| V2EX | ✅ | ✅ | 公开 |
| LinkedIn | ✅ | ✅ | Cookie |
| YouTube | ✅ | ✅ | yt-dlp |
| 微信公众号 | - | ✅ | Cookie |
| RSS | - | ✅ | URL |
| 小宇宙 | - | ✅ | 公开 |
| 雪球 | ✅ | ✅ | 公开 |

## 零配置命令

### 通用Jina Reader

```bash
curl -s "https://r.jina.ai/<URL>"
```

### Exa搜索

```bash
mcporter call 'exa.web_search_exa(query: "搜索词", numResults: 5)'
```

### GitHub

```bash
# 搜索仓库
gh search repos "关键词" --sort stars --limit 10

# 搜索代码
gh search code "关键词" --language python

# 查看Issue
gh issue list --repo owner/repo

# 查看PR
gh pr list --repo owner/repo
```

### Twitter/X

```bash
twitter search "关键词" --limit 10
twitter user "@username" --limit 10
```

### Reddit

```bash
rdt search "关键词" --limit 10
rdt read <POST_ID>
```

### 小红书

```bash
xhs search "关键词" --limit 10
xhs read <NOTE_ID>
```

### YouTube/B站

```bash
# 获取字幕
yt-dlp --write-sub --skip-download -o "/tmp/%(id)s" "URL"

# 获取自动生成字幕
yt-dlp --write-auto-sub --skip-download -o "/tmp/%(id)s" "URL"

# 下载音频
yt-dlp -x --audio-format mp3 -o "/tmp/%(title)s.%(ext)s" "URL"
```

## API调用

```python
from agent_reach import AgentReach

# 网页搜索
reach = AgentReach()
results = reach.search("Python async programming best practices")

# URL读取
content = reach.read("https://example.com/article")
```

## 环境诊断

```bash
agent-reach doctor
```

输出示例：
```
✅ Python 3.11+
✅ gh (GitHub CLI)
✅ twitter
✅ rdt (Reddit)
✅ yt-dlp
⚠️  xhs — 需要配置Cookie
⚠️  twitter — 需要配置Cookie
```

## 配置渠道

```bash
python -m agent_reach.cli install --env=auto
```

## 工作区规则

- **不要在Agent工作区创建文件**
- 临时输出放 `/tmp/`
- 持久数据放 `~/.agent-reach/`
- Cookie认证使用Cookie-Editor浏览器导出格式

## MCP工具

```bash
mcporter_list_servers()   # 列出所有MCP服务
mcporter start            # 启动MCP Server
```
