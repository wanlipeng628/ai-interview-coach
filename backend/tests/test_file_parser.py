"""Tests for resume file parser."""

from io import BytesIO

import pytest

from app.application.resume.file_parser import (
    UnsupportedFileTypeError,
    parse_resume_file,
)


class TestParseTextFile:
    def test_txt_utf8(self) -> None:
        content = "张三\n后端工程师\n5年经验"
        result = parse_resume_file("resume.txt", content.encode("utf-8"))
        assert "张三" in result
        assert "后端工程师" in result

    def test_txt_gbk_fallback(self) -> None:
        content = "李四\nJava开发"
        result = parse_resume_file("resume.txt", content.encode("gbk"))
        assert "李四" in result
        assert "Java开发" in result

    def test_md_file(self) -> None:
        content = "# 王五\n## 技能\n- Python\n- Go"
        result = parse_resume_file("resume.md", content.encode("utf-8"))
        assert "王五" in result
        assert "Python" in result


class TestParsePdfFile:
    def _make_minimal_pdf(self) -> bytes:
        """生成一个最小有效 PDF（空白页）。"""
        from pypdf import PdfWriter

        writer = PdfWriter()
        writer.add_blank_page(width=612, height=792)
        buf = BytesIO()
        writer.write(buf)
        return buf.getvalue()

    def test_pdf_blank_returns_empty_string(self) -> None:
        pdf_bytes = self._make_minimal_pdf()
        result = parse_resume_file("resume.pdf", pdf_bytes)
        assert result == ""

    def test_pdf_invalid_content_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="Failed to parse PDF"):
            parse_resume_file("resume.pdf", b"not a real pdf")


class TestParseDocxFile:
    def _make_docx(self, paragraphs: list[str]) -> bytes:
        from docx import Document

        doc = Document()
        for p in paragraphs:
            doc.add_paragraph(p)
        buf = BytesIO()
        doc.save(buf)
        return buf.getvalue()

    def test_docx_paragraphs(self) -> None:
        docx_bytes = self._make_docx(["赵六", "前端工程师", "React, Vue, TypeScript"])
        result = parse_resume_file("resume.docx", docx_bytes)
        assert "赵六" in result
        assert "前端工程师" in result
        assert "React" in result

    def test_docx_empty_paragraphs_skipped(self) -> None:
        docx_bytes = self._make_docx(["", "  ", "有效内容", ""])
        result = parse_resume_file("resume.docx", docx_bytes)
        assert result == "有效内容"

    def test_docx_invalid_content_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="Failed to parse DOCX"):
            parse_resume_file("resume.docx", b"not a real docx")


class TestUnsupportedFileType:
    @pytest.mark.parametrize("filename", [
        "resume.doc",
        "resume.rtf",
        "resume.jpg",
        "resume.xlsx",
        "resume",
    ])
    def test_unsupported_extensions(self, filename: str) -> None:
        with pytest.raises(UnsupportedFileTypeError):
            parse_resume_file(filename, b"fake content")

    def test_error_message_contains_extension(self) -> None:
        with pytest.raises(UnsupportedFileTypeError, match=r"\.rtf"):
            parse_resume_file("resume.rtf", b"data")

    def test_case_insensitive_extension_txt(self) -> None:
        content = "钱七\n测试工程师"
        result = parse_resume_file("resume.TXT", content.encode("utf-8"))
        assert "钱七" in result

    def test_case_insensitive_extension_md(self) -> None:
        content = "# 孙八"
        result = parse_resume_file("resume.MD", content.encode("utf-8"))
        assert "孙八" in result
