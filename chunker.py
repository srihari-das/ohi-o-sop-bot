import re

# Lines that start with these patterns are list items, never section headers.
_LIST_ITEM_RE = re.compile(r'^(\s+|[\*\-\•\+\>]|\d+[\.\)]\s)')


def _is_header(line: str, next_line: str) -> bool:
    """Return True if line looks like a section header, not a bullet or body text."""
    stripped = line.strip()

    if not stripped:
        return False

    # Must not be indented — real headers start at column 0
    if line[0] == ' ' or line[0] == '\t':
        return False

    # Must not be a bullet point or numbered list item
    if _LIST_ITEM_RE.match(stripped):
        return False

    # Must start with a capital letter (section titles are capitalised)
    if not stripped[0].isupper():
        return False

    # Must be short — genuine headers are concise
    if len(stripped) >= 80:
        return False

    # Must not end with sentence-ending punctuation or a colon mid-sentence
    if stripped[-1] in '.?!,;':
        return False

    # Must not be purely numeric
    if re.fullmatch(r'[\d\s.]+', stripped):
        return False

    # Must be followed by a blank line or non-empty content (rules out stray one-liners
    # at the very end of a file, but allows headers followed directly by bullets)
    next_stripped = next_line.strip() if next_line is not None else ''
    if next_stripped == '' and line == next_line:
        # no next line at all — skip
        return False

    return True


def _detect_headers(lines: list[str]) -> list[int]:
    """Return indices of lines that are section headers."""
    header_indices = []
    for i, line in enumerate(lines):
        next_line = lines[i + 1] if i + 1 < len(lines) else None
        if _is_header(line, next_line):
            header_indices.append(i)
    return header_indices


def _chunk_by_headers(lines: list[str], header_indices: list[int]) -> list[str]:
    """Split lines into chunks at each header boundary.

    Every chunk starts with its own header and contains all content
    (bullets, paragraphs, etc.) up to the next header.
    """
    chunks = []
    # Content before the first header gets its own chunk with no prefix
    if header_indices[0] > 0:
        pre = '\n'.join(lines[:header_indices[0]]).strip()
        if pre:
            chunks.append(pre)
    pending_header = None
    for j, start in enumerate(header_indices):
        end = header_indices[j + 1] if j + 1 < len(header_indices) else len(lines)
        chunk = '\n'.join(lines[start:end]).strip()
        if not chunk:
            continue
        header_only = chunk == lines[start].strip()
        if header_only:
            # No body — carry this header forward as a prefix for the next chunk
            pending_header = chunk
            continue
        if pending_header:
            chunk = f'{pending_header}\n{chunk}'
            pending_header = None
        chunks.append(chunk)
    # If the last header had no following chunk to absorb it, drop it silently
    return chunks


def _split_paragraphs(text: str) -> list[str]:
    """Split on one or more blank lines."""
    paragraphs = re.split(r'\n[ \t]*\n', text)
    return [p.strip() for p in paragraphs if p.strip()]


def _merge_short_paragraphs(paragraphs: list[str], min_len: int = 100) -> list[str]:
    """Merge consecutive short paragraphs so trivially small chunks don't pollute the index."""
    merged = []
    buffer = ''
    for p in paragraphs:
        buffer = f'{buffer}\n\n{p}' if buffer else p
        if len(buffer) >= min_len:
            merged.append(buffer)
            buffer = ''
    if buffer:
        if merged:
            merged[-1] = f'{merged[-1]}\n\n{buffer}'
        else:
            merged.append(buffer)
    return merged


def _fixed_size_chunks(text: str, chunk_size: int = 400, overlap: int = 50) -> list[str]:
    """Split text into fixed-size word chunks with overlap.

    Uses whitespace-split words as a proxy for tokens.
    """
    words = text.split()
    if not words:
        return []
    chunks = []
    start = 0
    while start < len(words):
        end = start + chunk_size
        chunks.append(' '.join(words[start:end]))
        if end >= len(words):
            break
        start = end - overlap
    return chunks


def chunk_document(text: str, doc_name: str) -> list[dict]:
    """Chunk a document using a three-tier hybrid strategy.

    Returns a list of dicts with keys:
        text, chunk_index, chunking_tier
    """
    lines = text.splitlines()

    # --- Tier 1: Header-based ---
    header_indices = _detect_headers(lines)
    if len(header_indices) >= 3:
        chunks = _chunk_by_headers(lines, header_indices)
        tier = 1
        print(f'[ingest] "{doc_name}" → {len(chunks)} chunks (tier 1: header-based)')
        return [{'text': c, 'chunk_index': i, 'chunking_tier': tier} for i, c in enumerate(chunks)]

    # --- Tier 2: Paragraph-based ---
    paragraphs = _split_paragraphs(text)
    if len(paragraphs) >= 2:
        chunks = _merge_short_paragraphs(paragraphs)
        tier = 2
        print(f'[ingest] "{doc_name}" → {len(chunks)} chunks (tier 2: paragraph-based)')
        return [{'text': c, 'chunk_index': i, 'chunking_tier': tier} for i, c in enumerate(chunks)]

    # --- Tier 3: Fixed-size fallback ---
    chunks = _fixed_size_chunks(text, chunk_size=400, overlap=50)
    tier = 3
    print(f'[ingest] "{doc_name}" → {len(chunks)} chunks (tier 3: fixed-size fallback)')
    return [{'text': c, 'chunk_index': i, 'chunking_tier': tier} for i, c in enumerate(chunks)]
