"""文档处理器 OCR 性能优化测试模块.

验证单例模式、懒加载、并发安全、文件头验证及性能提升。
"""

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.document_processor import (
    SUPPORTED_OCR_EXTENSIONS,
    _validate_file_header,
)


class TestFileHeaderValidation:
    """文件头验证测试."""

    def test_valid_jpeg_header(self):
        content = (
            b"\xff\xd8\xff\xe0\x00\x10JFIF"
            b"\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
        )
        assert _validate_file_header(content) is True

    def test_valid_png_header(self):
        content = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
        assert _validate_file_header(content) is True

    def test_valid_webp_header(self):
        content = b"RIFF\x00\x00\x00\x00WEBP"
        assert _validate_file_header(content) is True

    def test_valid_bmp_header(self):
        content = b"BM\x00\x00\x00\x00\x00\x00\x00\x00"
        assert _validate_file_header(content) is True

    def test_valid_gif_header(self):
        content = b"GIF89a\x00\x00\x00\x00"
        assert _validate_file_header(content) is True

    def test_valid_tiff_big_endian_header(self):
        content = b"MM\x00\x2a\x00\x00\x00\x00"
        assert _validate_file_header(content) is True

    def test_valid_tiff_little_endian_header(self):
        content = b"II\x2a\x00\x00\x00\x00\x00"
        assert _validate_file_header(content) is True

    def test_invalid_text_file_header(self):
        content = b"Hello, this is a text file."
        assert _validate_file_header(content) is False

    def test_invalid_pdf_header(self):
        content = b"%PDF-1.4 fake pdf content"
        assert _validate_file_header(content) is False

    def test_invalid_empty_content(self):
        content = b""
        assert _validate_file_header(content) is False

    def test_invalid_random_binary(self):
        content = b"\x00\x01\x02\x03\x04\x05\x06\x07"
        assert _validate_file_header(content) is False


class TestOcrSingleton:
    """PaddleOCR 单例模式测试."""

    @patch("app.services.document_processor._init_ocr")
    def test_same_instance_returned_on_multiple_calls(self, mock_init):
        mock_ocr = MagicMock()
        mock_ocr.ocr = MagicMock(
            return_value=[[[[[0, 0], [10, 0], [10, 10], [0, 10]], ("test", 0.99)]]]
        )
        mock_init.return_value = mock_ocr

        async def run():
            import app.services.document_processor as dp  # noqa: PLC0415

            dp._ocr_instance = None
            i1 = await dp._get_ocr()
            i2 = await dp._get_ocr()
            return i1, i2

        instance1, instance2 = asyncio.run(run())

        assert instance1 is instance2
        assert mock_init.call_count == 1

    @patch("app.services.document_processor._init_ocr")
    def test_instance_not_created_until_first_call(self, mock_init):
        import app.services.document_processor as dp  # noqa: PLC0415

        dp._ocr_instance = None
        assert dp._ocr_instance is None
        assert mock_init.call_count == 0


class TestConcurrentSafety:
    """并发安全性测试."""

    @patch("app.services.document_processor._init_ocr")
    def test_concurrent_access_only_one_initialization(self, mock_init):
        import app.services.document_processor as dp  # noqa: PLC0415

        dp._ocr_instance = None
        call_count = 0
        active_coros = 0
        max_concurrent = 0

        def slow_init():
            nonlocal call_count, active_coros, max_concurrent
            call_count += 1
            active_coros += 1
            max_concurrent = max(max_concurrent, active_coros)
            time.sleep(0.05)
            active_coros -= 1
            return MagicMock()

        mock_init.side_effect = slow_init

        async def concurrent_get():
            return await dp._get_ocr()

        async def run_concurrently():
            tasks = [
                concurrent_get() for _ in range(10)
            ]
            return await asyncio.gather(*tasks)

        results = asyncio.run(run_concurrently())

        first = results[0]
        for r in results:
            assert r is first
        assert call_count == 1


class TestOcrFileValidation:
    """OCR 文件验证集成测试."""

    @patch("app.services.document_processor._get_ocr")
    @patch("app.services.document_processor._validate_file_header")
    async def test_ocr_with_valid_image(self, mock_validate, mock_get_ocr):
        mock_validate.return_value = True
        mock_ocr = MagicMock()
        mock_ocr.ocr = MagicMock(
            return_value=[[[[[0, 0], [10, 0], [10, 10], [0, 10]], ("识别文本", 0.98)]]]
        )
        mock_get_ocr.return_value = mock_ocr

        from app.services.document_processor import process_ocr  # noqa: PLC0415

        mock_file = AsyncMock()
        mock_file.filename = "test.png"
        mock_file.read = AsyncMock(return_value=b"\x89PNG\r\n\x1a\nfake_image")

        result = await process_ocr(mock_file)
        assert result == "识别文本"

    @patch("app.services.document_processor._get_ocr")
    @patch("app.services.document_processor._validate_file_header")
    async def test_ocr_with_invalid_image(self, mock_validate, mock_get_ocr):
        mock_validate.return_value = False

        from app.services.document_processor import process_ocr  # noqa: PLC0415

        mock_file = AsyncMock()
        mock_file.filename = "fake.png"
        mock_file.read = AsyncMock(return_value=b"This is not an image")

        with pytest.raises(ValueError, match="文件头校验失败"):
            await process_ocr(mock_file)

        mock_get_ocr.assert_not_called()


class TestDocumentRouting:
    """文档路由扩展支持测试."""

    def test_supported_ocr_extensions(self):
        extensions = SUPPORTED_OCR_EXTENSIONS
        assert ".png" in extensions
        assert ".jpg" in extensions
        assert ".jpeg" in extensions
        assert ".webp" in extensions
        assert ".bmp" in extensions
        assert ".gif" in extensions
        assert ".tiff" in extensions
        assert ".tif" in extensions


class TestPerformance:
    """性能基准测试."""

    @patch("app.services.document_processor._init_ocr")
    def test_singleton_avoids_repeated_init(self, mock_init):
        import app.services.document_processor as dp  # noqa: PLC0415

        dp._ocr_instance = None
        mock_ocr = MagicMock()
        mock_ocr.ocr = MagicMock(
            return_value=[[[[[0, 0], [10, 0], [10, 10], [0, 10]], ("test", 0.99)]]]
        )
        mock_init.return_value = mock_ocr

        async def call_get_ocr(n):
            for _ in range(n):
                await dp._get_ocr()

        n_calls = 5
        start = time.perf_counter()
        asyncio.run(call_get_ocr(n_calls))
        elapsed = time.perf_counter() - start

        assert mock_init.call_count == 1
        assert elapsed < 1.0

    @patch("app.services.document_processor._init_ocr")
    def test_lazy_loading_no_init_on_import(self, mock_init):
        assert mock_init.call_count == 0


class TestThreadPoolInit:
    """线程池初始化测试."""

    @patch("app.services.document_processor.asyncio.to_thread")
    async def test_ocr_init_uses_to_thread(self, mock_to_thread):
        import app.services.document_processor as dp  # noqa: PLC0415

        dp._ocr_instance = None
        mock_ocr = MagicMock()
        mock_ocr.ocr = MagicMock(return_value=[[["test", 0.99]]])
        mock_to_thread.return_value = mock_ocr

        result = await dp._get_ocr()
        assert result is mock_ocr
        mock_to_thread.assert_called_once_with(dp._init_ocr)
