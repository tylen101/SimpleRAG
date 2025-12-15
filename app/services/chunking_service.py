from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple

from services.extraction_service import ExtractResult, PageText


@dataclass
class ChunkSpec:
    chunk_index: int
    page_start: Optional[int]
    page_end: Optional[int]
    section_path: Optional[str]
    token_count: Optional[int]
    chunk_text: str


def chunk_extracted(
    extracted: ExtractResult,
    max_chars: int = 5000,
    min_chars: int = 800,
) -> List[ChunkSpec]:
    """
    MVP chunking:
    - For PDF: split per page into paragraphs; pack into ~max_chars chunks.
    - For docx/text: treat as single page.
    - Stores page_start/page_end for citations.
    """
    pages: List[PageText] = extracted.pages

    # Build (page_num, paragraph_text) stream
    stream: List[Tuple[int, str]] = []
    for p in pages:
        # split into paragraphs
        paras = [x.strip() for x in p.text.split("\n\n") if x.strip()]
        if not paras:
            continue
        for para in paras:
            stream.append((p.page, para))

    chunks: List[ChunkSpec] = []
    if not stream:
        return chunks

    buf: List[str] = []
    buf_len = 0
    start_page: Optional[int] = None
    end_page: Optional[int] = None
    idx = 0

    def flush():
        nonlocal idx, buf, buf_len, start_page, end_page
        if not buf:
            return
        text = "\n\n".join(buf).strip()
        if not text:
            return
        chunks.append(
            ChunkSpec(
                chunk_index=idx,
                page_start=start_page,
                page_end=end_page,
                section_path=None,
                token_count=None,  # optional; can compute later using tokenizer
                chunk_text=text,
            )
        )
        idx += 1
        buf = []
        buf_len = 0
        start_page = None
        end_page = None

    for page_num, para in stream:
        if start_page is None:
            start_page = page_num
        end_page = page_num

        # If adding this paragraph would exceed max_chars, flush first (as long as we have enough content)
        projected = buf_len + len(para) + (2 if buf else 0)
        if buf and projected > max_chars and buf_len >= min_chars:
            flush()
            start_page = page_num
            end_page = page_num

        buf.append(para)
        buf_len += len(para) + (2 if buf_len else 0)

    flush()
    return chunks
