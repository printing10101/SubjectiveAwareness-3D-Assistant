"""启动独立推理服务.

在 8001 端口启动推理代理，转发请求到上游 Ollama 实例。
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

import uvicorn
from loguru import logger

from app.config import settings


if __name__ == "__main__":
    host: str = settings.INFERENCE_HOST
    port: int = settings.INFERENCE_PORT
    logger.info(f"启动推理服务: {host}:{port}")
    uvicorn.run(
        "ml.inference.server:app",
        host=host,
        port=port,
        reload=False,
    )
