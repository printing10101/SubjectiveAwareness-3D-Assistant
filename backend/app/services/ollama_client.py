"""Ollama LLM 统一调用客户端.

提供连接池复用、动态超时、请求限流和队列批处理能力。
模块级单例，应用启动时初始化，关闭时释放。
"""

import asyncio
import contextlib
import json
import re
from asyncio import Queue, Semaphore, Task
from typing import Any

import httpx
import tenacity
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import AnalysisConfig, settings


_HTTP_STATUS_SERVER_ERROR = 500
_HTTP_STATUS_OK = 200
_QUEUE_HISTORY_MAX = 1000


def _extract_think_content(raw: str) -> tuple[str, str]:
    """从 LLM 原始响应中提取 <think/> 标签内的推理过程和标签外的 JSON 文本.

    Args:
        raw: LLM 返回的原始响应文本

    Returns:
        tuple[str, str]: (推理过程文本, JSON 文本)
            若无 <think/> 标签，推理过程为空字符串，JSON 文本为原始响应全文
    """
    pattern = r" thinking(.*?) response"
    match = re.search(pattern, raw, re.DOTALL)
    if match:
        reasoning_text = match.group(1).strip()
        json_text = raw[match.end():].strip()
        return reasoning_text, json_text
    return "", raw


_MARKDOWN_FENCE_START = re.compile(r"```(?:json)?\s*\n")

_FENCE_RE = re.compile(r"```", re.MULTILINE)


def _strip_markdown_fences(text: str) -> str:
    match = _MARKDOWN_FENCE_START.search(text)
    if not match:
        return text

    content_start = match.end()
    remaining = text[content_start:]

    closing_matches = list(_FENCE_RE.finditer(remaining))
    if closing_matches:
        content_end = closing_matches[0].start()
        return remaining[:content_end].strip()

    return text


def _build_dynamic_timeout(prompt: str) -> httpx.Timeout:
    """根据提示词长度动态计算超时时间.

    Args:
        prompt: 输入提示文本

    Returns:
        httpx.Timeout: 动态计算后的超时配置
    """
    base = settings.OLLAMA_TIMEOUT_BASE
    per_1k = settings.OLLAMA_TIMEOUT_PER_1000_CHARS
    max_timeout = settings.OLLAMA_TIMEOUT_MAX
    dynamic = min(base + (len(prompt) // 1000) * per_1k, max_timeout)
    return httpx.Timeout(dynamic, connect=settings.OLLAMA_CONNECT_TIMEOUT)


class OllamaClient:
    """LLM 调用客户端，使用连接池复用 HTTP 连接.

    Attributes:
        client: 共享的 httpx.AsyncClient 实例（带连接池限制）
    """

    def __init__(self) -> None:
        self.client: httpx.AsyncClient = httpx.AsyncClient(
            timeout=httpx.Timeout(
                AnalysisConfig.OLLAMA_PIPELINE_TIMEOUT,
                connect=settings.OLLAMA_CONNECT_TIMEOUT,
            ),
            limits=httpx.Limits(
                max_connections=settings.OLLAMA_MAX_CONNECTIONS,
                max_keepalive_connections=settings.OLLAMA_MAX_KEEPALIVE_CONNECTIONS,
                keepalive_expiry=settings.OLLAMA_KEEPALIVE_EXPIRY,
            ),
        )

    @staticmethod
    def _extract_think_content(raw: str) -> tuple[str, str]:
        """从 LLM 原始响应中提取 <think/> 标签内的推理过程.

        Args:
            raw: LLM 返回的原始响应文本

        Returns:
            tuple[str, str]: (推理过程文本, JSON 文本)
        """
        return _extract_think_content(raw)

    async def generate(
        self,
        prompt: str,
        system_prompt: str = "",
        model: str | None = None,
        temperature: float = AnalysisConfig.OLLAMA_DEFAULT_TEMPERATURE,
        dynamic_timeout: bool = True,
    ) -> str:
        """发送 LLM 生成请求，复用连接池客户端.

        Args:
            prompt: 用户提示词
            system_prompt: 系统提示词（可选）
            model: 模型名称，默认使用配置中的模型
            temperature: 生成温度
            dynamic_timeout: 是否启用动态超时

        Returns:
            str: LLM 生成的响应文本

        Raises:
            httpx.HTTPError: HTTP 请求失败
            httpx.TimeoutException: 请求超时
        """
        url: str = f"{settings.OLLAMA_BASE_URL}/api/generate"
        payload: dict[str, Any] = {
            "model": model or settings.OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_ctx": AnalysisConfig.OLLAMA_NUM_CTX,
                "top_p": AnalysisConfig.OLLAMA_TOP_P,
                "num_predict": AnalysisConfig.OLLAMA_NUM_PREDICT,
                "repeat_penalty": AnalysisConfig.OLLAMA_REPEAT_PENALTY,
            },
        }
        if system_prompt:
            payload["system"] = system_prompt

        timeout = _build_dynamic_timeout(prompt) if dynamic_timeout else None

        last_exc: Exception | None = None
        for attempt in range(settings.OLLAMA_RETRY_MAX_ATTEMPTS + 1):
            try:
                response = await self.client.post(url, json=payload, timeout=timeout)
                response.raise_for_status()
                result: dict[str, Any] = response.json()
                return str(result.get("response", ""))
            except httpx.TimeoutException:
                last_exc = httpx.TimeoutException(
                    f"Ollama 请求超时 "
                    f"(尝试 {attempt + 1}/{settings.OLLAMA_RETRY_MAX_ATTEMPTS + 1})"
                )
                logger.warning(
                    f"Ollama 超时 (尝试 {attempt + 1}), prompt长度={len(prompt)}"
                )
            except httpx.HTTPStatusError as e:
                is_server_error = e.response.status_code >= _HTTP_STATUS_SERVER_ERROR
                can_retry = attempt < settings.OLLAMA_RETRY_MAX_ATTEMPTS
                if is_server_error and can_retry:
                    delay = settings.OLLAMA_RETRY_DELAY * (attempt + 1)
                    logger.warning(f"Ollama 服务错误 {e.response.status_code}, {delay}s 后重试")
                    await asyncio.sleep(delay)
                    last_exc = e
                    continue
                raise
            except (httpx.ConnectError, httpx.ConnectTimeout):
                if attempt < settings.OLLAMA_RETRY_MAX_ATTEMPTS:
                    delay = settings.OLLAMA_RETRY_DELAY * (attempt + 1)
                    logger.warning(f"Ollama 连接失败, {delay}s 后重试")
                    await asyncio.sleep(delay)
                    last_exc = None
                    continue
                raise

        raise last_exc or RuntimeError("Ollama 请求失败")

    async def generate_json(
        self,
        prompt: str,
        system_prompt: str = "",
        model: str | None = None,
        temperature: float = AnalysisConfig.OLLAMA_DEFAULT_TEMPERATURE,
        field: str | None = None,
    ) -> dict[str, Any] | list[Any]:
        """调用 LLM 并解析 JSON 响应.

        自动从响应中提取 JSON 内容（处理 Markdown 包裹、
        <think/> 思维链标签等情况）。

        Args:
            prompt: 用户提示词
            system_prompt: 系统提示词（可选）
            model: 模型名称
            temperature: 生成温度
            field: 从结果中提取指定字段（可选）

        Returns:
            解析后的 JSON dict 或 list
        """
        raw: str = await self.generate(prompt, system_prompt, model, temperature)

        reasoning_text, json_content = self._extract_think_content(raw)

        if reasoning_text:
            logger.debug("模型思维链推理过程:\n{}", reasoning_text)

        json_content = _strip_markdown_fences(json_content)

        start: int = json_content.find("{")
        list_start: int = json_content.find("[")
        if 0 <= list_start < start or start < 0:
            start = list_start

        if start >= 0:
            try:
                decoder = json.JSONDecoder()
                data, _ = decoder.raw_decode(json_content[start:])
                if reasoning_text and isinstance(data, dict):
                    data["reasoning_process"] = reasoning_text
                if field and isinstance(data, dict):
                    return data.get(field, data)
                return data
            except json.JSONDecodeError:
                pass

        logger.warning(f"无法从响应中提取 JSON: {raw[:200]}...")
        return {}

    async def list_models(self) -> list[dict[str, Any]]:
        """获取可用模型列表（对应 /api/tags）.

        Returns:
            list[dict[str, Any]]: 模型信息列表，每个元素包含 name 等模型属性
        """
        try:
            response = await self.client.get(
                f"{settings.OLLAMA_BASE_URL}/api/tags",
                timeout=httpx.Timeout(
                    AnalysisConfig.HEALTH_CHECK_TIMEOUT,
                    connect=settings.OLLAMA_CONNECT_TIMEOUT,
                ),
            )
            response.raise_for_status()
            data: dict[str, Any] = response.json()
            return list(data.get("models", []))
        except (httpx.HTTPError, json.JSONDecodeError):
            return []

    async def check_health(self) -> bool:
        """快速健康检查.

        Returns:
            bool: Ollama 服务是否可用
        """
        try:
            response = await self.client.get(
                f"{settings.OLLAMA_BASE_URL}/api/tags",
                timeout=httpx.Timeout(
                    AnalysisConfig.HEALTH_CHECK_TIMEOUT,
                    connect=settings.OLLAMA_CONNECT_TIMEOUT,
                ),
            )
            return response.status_code == _HTTP_STATUS_OK
        except httpx.HTTPError:
            return False

    async def check_model_available(self, model: str | None = None) -> bool:
        """检查指定模型是否可用.

        Args:
            model: 模型名称，默认使用配置中的模型

        Returns:
            bool: 模型是否在可用列表中
        """
        target = model or settings.OLLAMA_MODEL
        models = await self.list_models()
        model_names = [m.get("name", "") for m in models]
        model_prefix = target.split(":")[0]
        return target in model_names or any(model_prefix in m for m in model_names)

    async def close(self) -> None:
        """关闭连接池，释放资源."""
        await self.client.aclose()


class RateLimitedOllamaClient(OllamaClient):
    """带限流和队列功能的 LLM 调用客户端.

    通过信号量控制并发数，通过队列实现请求排队。
    """

    def __init__(self) -> None:
        super().__init__()
        self._semaphore = Semaphore(settings.OLLAMA_MAX_CONCURRENT)
        self._queue: Queue[tuple[str, dict, asyncio.Future]] = Queue(
            maxsize=settings.OLLAMA_QUEUE_MAXSIZE
        )
        self._worker_task: Task[Any] | None = None
        self._is_running: bool = False
        self._queue_size_history: list[int] = []

    @property
    def queue_size(self) -> int:
        """当前队列长度."""
        return self._queue.qsize()

    @property
    def average_queue_size(self) -> float:
        """历史平均队列长度."""
        if not self._queue_size_history:
            return 0.0
        return sum(self._queue_size_history) / len(self._queue_size_history)

    async def _worker(self) -> None:
        """后台工作协程，从队列中取请求执行."""
        while self._is_running:
            try:
                prompt, kwargs, future = await self._queue.get()
                self._queue_size_history.append(self._queue.qsize())
                if len(self._queue_size_history) > _QUEUE_HISTORY_MAX:
                    self._queue_size_history = self._queue_size_history[-_QUEUE_HISTORY_MAX:]
            except asyncio.CancelledError:
                break

            async with self._semaphore:
                try:
                    result = await self.generate(prompt, **kwargs)
                    if not future.done():
                        future.set_result(result)
                except Exception as e:  # noqa: BLE001
                    if not future.done():
                        future.set_exception(e)
                finally:
                    self._queue.task_done()

    def start_worker(self) -> None:
        """启动后台工作协程."""
        if not self._is_running:
            self._is_running = True
            self._worker_task = asyncio.create_task(self._worker())

    async def stop_worker(self) -> None:
        """停止后台工作协程."""
        self._is_running = False
        if self._worker_task:
            self._worker_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._worker_task
            self._worker_task = None

    async def enqueue_generate(
        self,
        prompt: str,
        **kwargs: Any,
    ) -> str:
        """将生成请求加入队列，由工作协程限流处理.

        Args:
            prompt: 用户提示词
            **kwargs: 传递给 generate() 的其他参数

        Returns:
            str: LLM 生成的响应文本
        """
        future: asyncio.Future[str] = asyncio.Future()
        await self._queue.put((prompt, kwargs, future))
        return await future

    async def batch_generate(
        self,
        prompts: list[str],
        **kwargs: Any,
    ) -> list[str]:
        """批量生成请求.

        Args:
            prompts: 输入提示文本列表
            **kwargs: 传递给每次 generate() 的共用参数

        Returns:
            list[str]: LLM 生成的文本结果列表
        """
        tasks = [self.enqueue_generate(p, **kwargs) for p in prompts]
        return await asyncio.gather(*tasks)


_client: OllamaClient | None = None
_rate_limited_client: RateLimitedOllamaClient | None = None


def get_client() -> OllamaClient:
    """获取全局 OllamaClient 单例."""
    global _client  # noqa: PLW0603
    if _client is None:
        _client = OllamaClient()
    return _client


def get_rate_limited_client() -> RateLimitedOllamaClient:
    """获取全局 RateLimitedOllamaClient 单例."""
    global _rate_limited_client  # noqa: PLW0603
    if _rate_limited_client is None:
        _rate_limited_client = RateLimitedOllamaClient()
    return _rate_limited_client


async def startup() -> None:
    """应用启动时初始化客户端（预检查 Ollama 可用性）."""
    client = get_client()
    available = await client.check_health()
    if available:
        model_ok = await client.check_model_available()
        if model_ok:
            logger.info("Ollama 模型 '{}' 可用。", settings.OLLAMA_MODEL)
        else:
            models = await client.list_models()
            logger.warning(
                "模型 '{}' 未找到。可用模型: {}",
                settings.OLLAMA_MODEL,
                [m.get("name", "") for m in models],
            )
    else:
        logger.warning("Ollama 服务不可用 ({}).", settings.OLLAMA_BASE_URL)

    get_rate_limited_client().start_worker()


async def shutdown() -> None:
    """应用关闭时释放连接池和队列资源."""
    await get_rate_limited_client().stop_worker()
    await get_client().close()
    if _rate_limited_client is not None:
        await _rate_limited_client.close()
    logger.info("Ollama 客户端连接池已释放。")


async def call_ollama(prompt: str, **kwargs: Any) -> str:
    """Ollama API 调用入口，全局单例客户端.

    封装 OllamaClient.generate()，提供统一的异步调用接口，
    便于测试 mock 和后续加入重试/监控逻辑。

    Args:
        prompt: 输入提示字符串
        **kwargs: 传递给 OllamaClient.generate 的额外参数

    Returns:
        str: LLM 生成的原始响应文本
    """
    client = get_client()
    return await client.generate(prompt, **kwargs)


@retry(
    stop=stop_after_attempt(AnalysisConfig.RETRY_MAX_ATTEMPTS),
    wait=wait_exponential(
        multiplier=AnalysisConfig.RETRY_WAIT_MULTIPLIER,
        min=AnalysisConfig.RETRY_WAIT_MIN,
        max=AnalysisConfig.RETRY_WAIT_MAX,
    ),
    retry=tenacity.retry_if_exception_type((httpx.HTTPError, json.JSONDecodeError)),
    reraise=True,
    before_sleep=lambda retry_state: logger.warning(
        "Ollama API 调用失败，准备重试 ({}/{}): 异常={}",
        retry_state.attempt_number,
        AnalysisConfig.RETRY_MAX_ATTEMPTS,
        retry_state.outcome.exception(),  # type: ignore[union-attr]
    ),
)
async def call_ollama_with_retry(prompt: str, **kwargs: Any) -> str:
    """带智能重试机制的 Ollama API 调用函数.

    使用 tenacity 库实现指数退避重试策略：
      - 最大重试次数: {AnalysisConfig.RETRY_MAX_ATTEMPTS}
      - 初始等待: {AnalysisConfig.RETRY_WAIT_MIN} 秒
      - 最大等待: {AnalysisConfig.RETRY_WAIT_MAX} 秒
      - 触发重试的异常类型: httpx.HTTPError、json.JSONDecodeError

    Args:
        prompt: 输入提示字符串
        **kwargs: 传递给 call_ollama 的额外参数

    Returns:
        str: 经 JSON 格式验证的有效响应字符串

    Raises:
        httpx.HTTPError: API 调用失败且重试次数耗尽时
        json.JSONDecodeError: 响应无法解析为 JSON 且重试次数耗尽时
    """
    response = await call_ollama(prompt, **kwargs)

    try:
        json.loads(response)
    except json.JSONDecodeError as e:
        logger.error(
            "Ollama 返回无效 JSON: {}. 响应片段(前200字符): {}",
            str(e),
            response[:200],
        )
        raise

    return response
