"""中间件模块.

包含应用级中间件实现，例如审计日志中间件。
"""

from app.middleware.audit import AuditLogMiddleware


__all__ = ["AuditLogMiddleware"]
