# Security Policy

## Supported Versions

仅最新 `main` 分支接收安全修复。

## Reporting a Vulnerability

请通过 GitHub Security Advisories 私信报告，勿在公开 Issue 中贴出可利用细节或真实案件材料。

## Scope Notes

- 本项目定位为司法辅助研究原型，**不构成法律意见**，不替代司法人员独立判断。
- 案例数据应保持脱敏/合成；禁止将真实身份证号、银行卡号、完整案卷原文入库。
- 仓库已通过 `.gitignore` 禁止 `.trae/`、`github可用skill/`、`crawl_judgments.py` 等无关内容再次入库。
- API 密钥、JWT 密钥请使用环境变量，勿写入代码或提交到 Git。
