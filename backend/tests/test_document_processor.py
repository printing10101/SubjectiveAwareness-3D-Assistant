from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import UploadFile

from app.services.document_processor import process_document


class TestProcessDocument:
    async def test_unsupported_file_type(self):
        mock_file = MagicMock(spec=UploadFile)
        mock_file.filename = "test.xyz"
        mock_file.read = AsyncMock(return_value=b"fallback text content")
        result = await process_document(mock_file)
        assert result == "fallback text content"

    async def test_no_filename(self):
        mock_file = MagicMock(spec=UploadFile)
        mock_file.filename = None
        mock_file.read = AsyncMock(return_value=b"")
        with pytest.raises(ValueError, match="无法识别的文件类型"):
            await process_document(mock_file)

    async def test_empty_filename(self):
        mock_file = MagicMock(spec=UploadFile)
        mock_file.filename = ""
        mock_file.read = AsyncMock(return_value=b"")
        with pytest.raises(ValueError, match="无法识别的文件类型"):
            await process_document(mock_file)

    async def test_text_file(self):
        mock_file = MagicMock(spec=UploadFile)
        mock_file.filename = "test.txt"
        mock_file.read = AsyncMock(return_value=b"plain text content")
        result = await process_document(mock_file)
        assert result == "plain text content"

    async def test_text_file_with_encoding(self):
        mock_file = MagicMock(spec=UploadFile)
        mock_file.filename = "test.txt"
        mock_file.read = AsyncMock(return_value="中文文本内容".encode())
        result = await process_document(mock_file)
        assert "中文文本内容" in result

    async def test_pdf_file(self):
        mock_file = MagicMock(spec=UploadFile)
        mock_file.filename = "test.pdf"
        mock_file.read = AsyncMock(return_value=b"%PDF-1.4 test content")

        with patch(
            "app.services.document_processor.process_pdf",
            new_callable=AsyncMock,
        ) as mock_pdf:
            mock_pdf.return_value = "extracted pdf text"
            result = await process_document(mock_file)
            assert result == "extracted pdf text"

    async def test_pdf_processing_error(self):
        mock_file = MagicMock(spec=UploadFile)
        mock_file.filename = "test.pdf"
        mock_file.read = AsyncMock(return_value=b"invalid pdf")

        with patch("fitz.open") as mock_open:
            mock_open.side_effect = Exception("PDF parse error")
            with pytest.raises(Exception, match="PDF parse error"):
                await process_document(mock_file)

    async def test_docx_file(self):
        mock_file = MagicMock(spec=UploadFile)
        mock_file.filename = "test.docx"
        mock_file.read = AsyncMock(return_value=b"PK\x03\x04 docx content")

        with patch(
            "app.services.document_processor.process_docx",
            new_callable=AsyncMock,
        ) as mock_docx:
            mock_docx.return_value = "extracted docx text"
            result = await process_document(mock_file)
            assert result == "extracted docx text"

    async def test_image_file(self):
        mock_file = MagicMock(spec=UploadFile)
        mock_file.filename = "test.png"
        mock_file.read = AsyncMock(return_value=b"image content")

        with patch(
            "app.services.document_processor.process_ocr",
            new_callable=AsyncMock,
        ) as mock_ocr:
            mock_ocr.return_value = "recognized text"
            result = await process_document(mock_file)
            assert result == "recognized text"

    async def test_jpg_file(self):
        mock_file = MagicMock(spec=UploadFile)
        mock_file.filename = "test.jpg"
        mock_file.read = AsyncMock(return_value=b"image content")

        with patch(
            "app.services.document_processor.process_ocr",
            new_callable=AsyncMock,
        ) as mock_ocr:
            mock_ocr.return_value = "ocr result"
            result = await process_document(mock_file)
            assert result == "ocr result"

    async def test_upper_case_extension(self):
        mock_file = MagicMock(spec=UploadFile)
        mock_file.filename = "TEST.TXT"
        mock_file.read = AsyncMock(return_value=b"content")
        result = await process_document(mock_file)
        assert result == "content"
