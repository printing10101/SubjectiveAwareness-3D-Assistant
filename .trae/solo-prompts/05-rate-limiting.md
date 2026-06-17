# Trae Solo 提示词 - 请求限流

## 任务目标
添加API请求限流功能，防止恶意请求和系统过载。

## 执行步骤

### 步骤1: 安装依赖
```bash
cd backend
pip install slowapi
```

### 步骤2: 创建限流配置
创建 `backend/app/middleware/rate_limit.py`：

```python
"""请求限流中间件.

使用slowapi实现基于Redis或内存的限流。
"""

from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request, HTTPException

from app.config import settings


# 创建限流器实例
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["100/minute"],  # 默认限制：每分钟100请求
)


def get_limiter() -> Limiter:
    """获取限流器实例."""
    return limiter


# 自定义限流错误处理
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    """处理限流异常."""
    raise HTTPException(
        status_code=429,
        detail="请求过于频繁，请稍后再试",
        headers={"Retry-After": str(exc.retry_after)} if hasattr(exc, "retry_after") else {}
    )
```

### 步骤3: 应用限流到路由
修改 `backend/app/main.py`：

```python
from fastapi import FastAPI, Request
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.middleware.rate_limit import limiter, rate_limit_handler

# 创建应用时添加限流
app = FastAPI(
    title="帮信罪主观明知智能分析系统",
    version="1.0.0",
)

# 注册限流器
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_handler)

# 为特定路由添加限流
@app.post("/api/analyze")
@limiter.limit("10/minute")  # 分析接口：每分钟10次
async def analyze_case(request: Request, ...):
    ...

@app.post("/api/cases")
@limiter.limit("30/minute")  # 创建案件：每分钟30次
async def create_case(request: Request, ...):
    ...

@app.post("/api/auth/login")
@limiter.limit("5/minute")   # 登录接口：每分钟5次，防止暴力破解
async def login(request: Request, ...):
    ...
```

### 步骤4: 添加限流响应头
创建 `backend/app/middleware/rate_limit_headers.py`：

```python
"""限流响应头中间件."""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class RateLimitHeadersMiddleware(BaseHTTPMiddleware):
    """添加限流相关响应头."""
    
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # 如果有限流信息，添加到响应头
        if hasattr(request.state, "view_rate_limit"):
            limit = request.state.view_rate_limit
            response.headers["X-RateLimit-Limit"] = str(limit.limit)
            response.headers["X-RateLimit-Remaining"] = str(limit.remaining)
            response.headers["X-RateLimit-Reset"] = str(limit.reset)
        
        return response
```

### 步骤5: 验证限流
```bash
cd backend

# 1. 启动服务
python run.py &
sleep 3

# 2. 测试正常请求
curl -X POST http://localhost:8000/api/analyze \
  -H "Content-Type: application/json" \
  -d '{"case_text": "测试案件", "mode": "auto"}'

# 3. 测试限流（快速发送11个请求）
for i in {1..11}; do
  curl -s -o /dev/null -w "%{http_code}\n" \
    -X POST http://localhost:8000/api/analyze \
    -H "Content-Type: application/json" \
    -d '{"case_text": "测试", "mode": "auto"}'
done
# 预期：前10个返回200，第11个返回429

# 4. 检查响应头
curl -I http://localhost:8000/api/analyze \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{"case_text": "测试", "mode": "auto"}' 2>/dev/null | grep -i rate

kill %1
```

### 步骤6: 提交代码
```bash
git add -A
git commit -m "security(backend): 添加API请求限流

- 安装slowapi限流库
- 配置不同接口的限流策略
- 分析接口：10/minute
- 创建案件：30/minute
- 登录接口：5/minute
- 添加限流响应头
- 所有测试通过"
```

## 完成标准
- [ ] slowapi已安装
- [ ] 限流中间件已配置
- [ ] 各路由有限流装饰器
- [ ] 超限时返回429状态码
- [ ] 包含限流响应头
- [ ] 代码已提交

## 验证命令
```bash
# 快速请求测试限流
for i in {1..12}; do
  curl -s -o /dev/null -w "%{http_code} " \
    -X POST http://localhost:8000/api/analyze \
    -H "Content-Type: application/json" \
    -d '{"case_text": "测试", "mode": "auto"}'
done
echo ""
# 预期输出: 200 200 200 200 200 200 200 200 200 200 429 429
```
