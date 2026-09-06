"""Resume file parser for extracting text from uploaded files."""

from pathlib import Path

SUPPORTED_EXTENSIONS = {".txt", ".md", ".pdf", ".docx"}


class UnsupportedFileTypeError(ValueError):
    """Raised when the uploaded file type is not supported."""


def parse_resume_file(filename: str, file_bytes: bytes) -> str:
    """Extract plain text from a resume file.

    Supports .txt / .md (direct decode), .pdf (pypdf), .docx (python-docx).
    Raises UnsupportedFileTypeError for unsupported extensions.
    """
    ext = Path(filename).suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise UnsupportedFileTypeError(
            f"Unsupported file type: {ext}. "
            f"Supported types: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
        )

    if ext in {".txt", ".md"}:
        return _parse_text(file_bytes)
    if ext == ".pdf":
        return _parse_pdf(file_bytes)
    if ext == ".docx":
        return _parse_docx(file_bytes)

    raise UnsupportedFileTypeError(f"Unsupported file type: {ext}")


def _parse_text(file_bytes: bytes) -> str:
    # 优先 utf-8，失败回退 gbk（兼容 Windows 中文文本文件）
    try:
        return file_bytes.decode("utf-8")
    except UnicodeDecodeError:
        return file_bytes.decode("gbk", errors="replace")


def _parse_pdf(file_bytes: bytes) -> str:
    from io import BytesIO

    from pypdf import PdfReader
    from pypdf.errors import PdfReadError

    try:
        reader = PdfReader(BytesIO(file_bytes))
    except PdfReadError as exc:
        raise ValueError(f"Failed to parse PDF file: {exc}") from exc

    pages = []
    for page in reader.pages:
        text = page.extract_text() or ""
        if text.strip():
            pages.append(text)
    return "\n".join(pages).strip()


def _parse_docx(file_bytes: bytes) -> str:
    from io import BytesIO
    from zipfile import BadZipFile

    from docx import Document
    from docx.opc.exceptions import PackageNotFoundError

    try:
        document = Document(BytesIO(file_bytes))
    except (PackageNotFoundError, BadZipFile) as exc:
        raise ValueError(f"Failed to parse DOCX file: {exc}") from exc

    paragraphs = [p.text for p in document.paragraphs if p.text.strip()]
    return "\n".join(paragraphs).strip()
