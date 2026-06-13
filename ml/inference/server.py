"""独立推理服务.

作为 Ollama 的代理，监听 8001 端口并转发请求到上游 Ollama 实例。
"""

import json
import sys
from http import HTTPStatus
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

import httpx
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from app.config import AnalysisConfig, settings


app = FastAPI(title="Inference Server", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


async def proxy_to_ollama(request: Request, endpoint: str) -> Response:
    """代理请求到上游 Ollama 实例.

    Args:
        request: 原始请求对象
        endpoint: 上游 API 端点路径

    Returns:
        Response: 上游的原始响应
    """
    upstream_url: str = f"{settings.OLLAMA_UPSTREAM_URL}/{endpoint}"

    body: bytes = await request.body()

    try:
        payload: dict[str, Any] = json.loads(body) if body else {}
    except json.JSONDecodeError:
        payload = {}

    timeout = AnalysisConfig.INFERENCE_PROXY_TIMEOUT
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(
            upstream_url,
            json=payload,
            headers={"Content-Type": "application/json"},
        )
        media_type: str = response.headers.get("content-type", "application/json")
        return Response(
            content=response.content,
            status_code=response.status_code,
            media_type=media_type,
        )


@app.post("/api/generate")
async def generate(request: Request) -> Response:
    """生成文本补全代理.

    Args:
        request: 原始请求

    Returns:
        Response: Ollama 生成结果
    """
    logger.info("代理 /api/generate → 上游 Ollama")
    return await proxy_to_ollama(request, "api/generate")


@app.post("/api/chat")
async def chat(request: Request) -> Response:
    """聊天补全代理.

    Args:
        request: 原始请求

    Returns:
        Response: Ollama 聊天结果
    """
    logger.info("代理 /api/chat → 上游 Ollama")
    return await proxy_to_ollama(request, "api/chat")


@app.get("/api/tags")
async def list_models() -> Response:
    """获取可用模型列表.

    Returns:
        Response: 模型列表响应
    """
    timeout = AnalysisConfig.OLLAMA_CHECK_TIMEOUT
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.get(f"{settings.OLLAMA_UPSTREAM_URL}/api/tags")
        media_type: str = response.headers.get("content-type", "application/json")
        return Response(
            content=response.content,
            status_code=response.status_code,
            media_type=media_type,
        )


@app.post("/api/embeddings")
async def embeddings(request: Request) -> Response:
    """生成嵌入向量代理.

    Args:
        request: 原始请求

    Returns:
        Response: 嵌入向量结果
    """
    return await proxy_to_ollama(request, "api/embeddings")


@app.get("/health")
async def health() -> dict[str, str]:
    """健康检查.

    Returns:
        dict: 包含服务和上游状态的字典
    """
    try:
        timeout = AnalysisConfig.HEALTH_CHECK_TIMEOUT
        async with httpx.AsyncClient(timeout=timeout) as client:
            upstream_url: str = settings.OLLAMA_UPSTREAM_URL
            response = await client.get(f"{upstream_url}/api/tags")
            upstream_status: str = (
                "available" if (response.status_code == HTTPStatus.OK) else "error"
            )
            return {
                "status": "healthy",
                "upstream": upstream_status,
            }
    except Exception:
        return {"status": "degraded", "upstream": "unavailable"}


if __name__ == "__main__":
    import uvicorn

    host: str = settings.INFERENCE_HOST
    port: int = settings.INFERENCE_PORT
    logger.info(f"启动推理服务: {host}:{port}")
    uvicorn.run(
        "ml.inference.server:app",
        host=settings.INFERENCE_HOST,
        port=settings.INFERENCE_PORT,
        reload=False,
    )
