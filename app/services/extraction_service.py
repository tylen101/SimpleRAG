from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import io


@dataclass
class PageText:
    page: int
    text: str
    char_len: int
    has_text: bool


@dataclass
class ExtractResult:
    method: str  # "pdf_text" | "docx" | "text"
    pages: List[PageText]  # for non-pdf, we just return page=1
    full_text: str
    structure: Dict[str, Any]  # JSON-safe dict with stats, errors, tool info


def _is_pdf(file_bytes: bytes, mime_type: Optional[str]) -> bool:
    if mime_type and "pdf" in mime_type.lower():
        return True
    return file_bytes[:5] == b"%PDF-"


def _is_docx(file_bytes: bytes, mime_type: Optional[str]) -> bool:
    # DOCX is a zip; we use mime type or zip header PK..
    if mime_type and "wordprocessingml" in mime_type.lower():
        return True
    return file_bytes[:2] == b"PK"


def extract_text(file_bytes: bytes, mime_type: Optional[str]) -> ExtractResult:
    if _is_pdf(file_bytes, mime_type):
        return _extract_pdf_text(file_bytes)
    if _is_docx(file_bytes, mime_type):
        # best-effort DOCX; if python-docx not installed or parsing fails, fall back to text
        try:
            return _extract_docx_text(file_bytes)
        except Exception as e:
            return _extract_plain_text(
                file_bytes, note_error=f"DOCX extraction failed: {e}"
            )
    return _extract_plain_text(file_bytes)


def _extract_pdf_text(file_bytes: bytes) -> ExtractResult:
    structure: Dict[str, Any] = {
        "extraction": {
            "method": "pdf_text",
            "tool": None,
            "errors": [],
            "ocr_needed": False,
            "ocr_reason": None,
        },
        "pages": [],
        "stats": {},
    }

    pages: List[PageText] = []

    # Prefer pypdf (lightweight)
    try:
        from pypdf import PdfReader  # type: ignore

        structure["extraction"]["tool"] = "pypdf"
        reader = PdfReader(io.BytesIO(file_bytes))
        num_pages = len(reader.pages)

        total_chars = 0
        empty_pages = 0

        for i in range(num_pages):
            try:
                txt = reader.pages[i].extract_text() or ""
            except Exception as e:
                structure["extraction"]["errors"].append(f"page {i+1}: {e}")
                txt = ""

            txt_norm = _normalize_text(txt)
            clen = len(txt_norm)
            has_text = clen > 20  # heuristic
            if not has_text:
                empty_pages += 1

            total_chars += clen
            pages.append(
                PageText(page=i + 1, text=txt_norm, char_len=clen, has_text=has_text)
            )
            structure["pages"].append(
                {"page": i + 1, "char_len": clen, "has_text": has_text}
            )

        # OCR heuristic: if most pages empty, mark OCR-needed (we don’t OCR yet)
        if num_pages > 0 and (empty_pages / num_pages) >= 0.6:
            structure["extraction"]["ocr_needed"] = True
            structure["extraction"][
                "ocr_reason"
            ] = f"{empty_pages}/{num_pages} pages had little/no text"

        structure["stats"] = {
            "num_pages": num_pages,
            "total_chars": total_chars,
            "empty_pages": empty_pages,
        }

        full_text = "\n\n".join(p.text for p in pages).strip()

        return ExtractResult(
            method="pdf_text",
            pages=pages,
            full_text=full_text,
            structure=structure,
        )

    except Exception as e:
        structure["extraction"]["errors"].append(f"PDF extraction failed: {e}")
        # fall back to plain decode attempt
        return _extract_plain_text(file_bytes, note_error=f"PDF extraction failed: {e}")


def _extract_docx_text(file_bytes: bytes) -> ExtractResult:
    structure: Dict[str, Any] = {
        "extraction": {
            "method": "docx",
            "tool": "python-docx",
            "errors": [],
            "ocr_needed": False,
            "ocr_reason": None,
        },
        "pages": [],
        "stats": {},
    }

    from docx import Document as DocxDocument  # type: ignore

    doc = DocxDocument(io.BytesIO(file_bytes))
    paras = []
    for p in doc.paragraphs:
        t = (p.text or "").strip()
        if t:
            paras.append(t)

    full_text = _normalize_text("\n\n".join(paras)).strip()
    pages = [
        PageText(
            page=1,
            text=full_text,
            char_len=len(full_text),
            has_text=len(full_text) > 20,
        )
    ]
    structure["pages"] = [
        {"page": 1, "char_len": len(full_text), "has_text": len(full_text) > 20}
    ]
    structure["stats"] = {
        "num_pages": 1,
        "total_chars": len(full_text),
        "empty_pages": 0,
    }

    return ExtractResult(
        method="docx", pages=pages, full_text=full_text, structure=structure
    )


def _extract_plain_text(
    file_bytes: bytes, note_error: Optional[str] = None
) -> ExtractResult:
    structure: Dict[str, Any] = {
        "extraction": {
            "method": "text",
            "tool": "utf-8/latin-1 decode",
            "errors": [],
            "ocr_needed": False,
            "ocr_reason": None,
        },
        "pages": [],
        "stats": {},
    }
    if note_error:
        structure["extraction"]["errors"].append(note_error)

    # Best-effort decoding
    try:
        txt = file_bytes.decode("utf-8")
    except Exception:
        txt = file_bytes.decode("latin-1", errors="ignore")

    full_text = _normalize_text(txt).strip()
    pages = [
        PageText(
            page=1,
            text=full_text,
            char_len=len(full_text),
            has_text=len(full_text) > 20,
        )
    ]
    structure["pages"] = [
        {"page": 1, "char_len": len(full_text), "has_text": len(full_text) > 20}
    ]
    structure["stats"] = {
        "num_pages": 1,
        "total_chars": len(full_text),
        "empty_pages": 0,
    }

    return ExtractResult(
        method="text", pages=pages, full_text=full_text, structure=structure
    )


def _normalize_text(s: str) -> str:
    # Keep it conservative for MVP: normalize line endings + trim trailing whitespace
    s = s.replace("\r\n", "\n").replace("\r", "\n")
    # collapse excessive blank lines
    while "\n\n\n" in s:
        s = s.replace("\n\n\n", "\n\n")
    return s.strip()
