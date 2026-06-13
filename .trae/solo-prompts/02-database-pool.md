# Trae Solo 提示词 - 数据库连接池优化

## 任务目标
为数据库连接添加连接池配置，提升并发性能和稳定性。

## 执行步骤

### 步骤1: 备份当前配置
```bash
cd backend
cp app/database.py app/database.py.bak
```

### 步骤2: 修改数据库配置
编辑 `app/database.py`，添加连接池参数：

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from app.config import settings

# 添加连接池配置
engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {},
    # 连接池配置
    pool_size=10,              # 基础连接数
    max_overflow=20,           # 最大溢出连接数
    pool_pre_ping=True,        # 连接前ping检测
    pool_recycle=3600,         # 连接回收时间(秒)
    pool_timeout=30,           # 获取连接超时时间
    echo=settings.DEBUG,       # 调试模式打印SQL
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """获取数据库会话."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

### 步骤3: 添加连接池监控（可选）
在 `app/utils/db_monitor.py` 创建监控工具：

```python
"""数据库连接池监控."""

from loguru import logger
from sqlalchemy import event
from sqlalchemy.engine import Engine

from app.database import engine


@event.listens_for(Engine, "connect")
def on_connect(dbapi_conn, connection_record):
    """连接建立时触发."""
    logger.debug("数据库连接已建立")


@event.listens_for(Engine, "checkout")
def on_checkout(dbapi_conn, connection_record, connection_proxy):
    """连接从池取出时触发."""
    logger.debug("数据库连接从连接池取出")


def get_pool_status():
    """获取连接池状态."""
    pool = engine.pool
    return {
        "size": pool.size(),           # 当前连接数
        "checked_in": pool.checkedin(),  # 空闲连接
        "checked_out": pool.checkedout(),  # 使用中连接
        "overflow": pool.overflow(),   # 溢出连接数
    }
```

### 步骤4: 验证配置
```bash
cd backend

# 1. 启动服务测试连接
python -c "
from app.database import engine
from app.utils.db_monitor import get_pool_status
print('连接池配置:', engine.pool.status())
print('连接池状态:', get_pool_status())
"

# 2. 运行测试
pytest tests/ -v -k "db" --tb=short

# 3. 检查SQLAlchemy版本兼容性
python -c "import sqlalchemy; print(f'SQLAlchemy版本: {sqlalchemy.__version__}')"
```

### 步骤5: 提交代码
```bash
git add -A
git commit -m "perf(backend): 添加数据库连接池配置

- 配置连接池大小: pool_size=10, max_overflow=20
- 添加连接健康检查: pool_pre_ping=True
- 添加连接回收机制: pool_recycle=3600
- 添加连接池监控工具
- 所有测试通过"
```

## 完成标准
- [ ] `app/database.py` 包含连接池配置
- [ ] 连接池参数正确设置
- [ ] 服务启动无错误
- [ ] 数据库测试通过
- [ ] 代码已提交

## 验证命令
```bash
# 验证连接池工作正常
python -c "
from app.database import engine
pool = engine.pool
print(f'Pool size: {pool.size()}')
print(f'Pool class: {pool.__class__.__name__}')
"
```
